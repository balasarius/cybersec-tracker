# SPDX-License-Identifier: Apache-2.0
"""Asset identity normalization, ambiguity, and analyst resolution tests."""

import uuid
from datetime import UTC, datetime

import pytest

from apps.accounts.models import User
from apps.assets.models import AliasType, Asset, AssetAlias, AssetType, ResolutionStatus
from apps.assets.services import (
    ResolutionKind,
    approve_asset_resolution,
    normalize_alias,
    resolve_asset,
)
from apps.audit.models import AuditEvent
from apps.integrations.models import SourceAccount, SourceKind
from apps.tenancy.models import (
    BusinessUnit,
    BusinessUnitGrant,
    MembershipRole,
    Organisation,
    OrganisationMembership,
)

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def context() -> tuple[Organisation, SourceAccount]:
    organisation = Organisation.objects.create(
        name=f"Org {uuid.uuid4()}", slug=f"org-{uuid.uuid4()}"
    )
    source = SourceAccount.objects.create(
        organisation=organisation, kind=SourceKind.TENABLE, name="Scanner"
    )
    return organisation, source


@pytest.mark.parametrize(
    ("kind", "raw", "expected"),
    [
        (AliasType.FQDN, " Host.Example.TEST. ", "host.example.test"),
        (AliasType.IP, "2001:0db8::1", "2001:db8::1"),
        (AliasType.MAC, "AA:BB:CC:DD:EE:FF", "aabbccddeeff"),
        (AliasType.PROVIDER_ID, " Provider-ABC ", "Provider-ABC"),
    ],
)
def test_normalize_alias(kind: str, raw: str, expected: str) -> None:
    assert normalize_alias(alias_type=kind, value=raw) == expected


def test_normalize_alias_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="empty"):
        normalize_alias(alias_type=AliasType.FQDN, value=" ")
    with pytest.raises(ValueError, match="MAC"):
        normalize_alias(alias_type=AliasType.MAC, value="invalid")
    with pytest.raises(ValueError, match="Unknown"):
        normalize_alias(alias_type="unknown", value="value")


def test_strong_single_match_is_exact_and_missing_is_unmatched() -> None:
    organisation, source = context()
    asset = Asset.objects.create(
        organisation=organisation, asset_type=AssetType.HOST, canonical_name="host"
    )
    AssetAlias.objects.create(
        organisation=organisation,
        asset=asset,
        source_account=source,
        alias_type=AliasType.FQDN,
        normalized_value="host.example.test",
        context="prod",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )

    exact = resolve_asset(
        source_account=source,
        alias_type=AliasType.FQDN,
        value="HOST.EXAMPLE.TEST.",
        context="prod",
    )
    missing = resolve_asset(
        source_account=source, alias_type=AliasType.FQDN, value="missing.example.test"
    )

    assert exact.kind == ResolutionKind.EXACT
    assert exact.asset == asset
    assert missing.kind == ResolutionKind.UNMATCHED
    assert missing.asset is None


def test_ip_match_requires_review_and_retry_reuses_case() -> None:
    organisation, source = context()
    asset = Asset.objects.create(
        organisation=organisation, asset_type=AssetType.HOST, canonical_name="host"
    )
    AssetAlias.objects.create(
        organisation=organisation,
        asset=asset,
        source_account=source,
        alias_type=AliasType.IP,
        normalized_value="192.0.2.10",
        context="network-a",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )

    first = resolve_asset(
        source_account=source,
        alias_type=AliasType.IP,
        value="192.0.2.10",
        context="network-a",
    )
    retry = resolve_asset(
        source_account=source,
        alias_type=AliasType.IP,
        value="192.0.2.10",
        context="network-a",
    )

    assert first.kind == ResolutionKind.REVIEW
    assert first.review_case == retry.review_case
    assert first.candidate_ids == (asset.id,)


def test_analyst_approves_resolution_with_audit() -> None:
    organisation, source = context()
    unit = BusinessUnit.objects.create(
        organisation=organisation, name="Sensitive", slug="sensitive", is_sensitive=True
    )
    asset = Asset.objects.create(
        organisation=organisation,
        business_unit=unit,
        asset_type=AssetType.HOST,
        canonical_name="host",
    )
    AssetAlias.objects.create(
        organisation=organisation,
        asset=asset,
        source_account=source,
        alias_type=AliasType.IP,
        normalized_value="192.0.2.11",
        context="",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    review = resolve_asset(
        source_account=source, alias_type=AliasType.IP, value="192.0.2.11"
    ).review_case
    assert review is not None
    analyst = User.objects.create_user(username="asset-analyst")
    membership = OrganisationMembership.objects.create(
        organisation=organisation, user=analyst, role=MembershipRole.SECURITY_ANALYST
    )
    BusinessUnitGrant.objects.create(membership=membership, business_unit=unit)
    analyst.is_verified = lambda: True  # type: ignore[attr-defined,method-assign]

    alias = approve_asset_resolution(
        review_case=review, asset=asset, analyst=analyst, reason="CMDB confirmation"
    )

    review.refresh_from_db()
    assert alias.asset == asset
    assert review.status == ResolutionStatus.RESOLVED
    event = AuditEvent.objects.get(action="asset.resolution_approved")
    assert event.reason == "CMDB confirmation"
