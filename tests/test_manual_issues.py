# SPDX-License-Identifier: Apache-2.0
"""Manual issue separation, scope, permission, and audit tests."""

import uuid
from datetime import UTC, datetime

import pytest

from apps.accounts.models import User
from apps.assets.models import Asset, AssetType
from apps.audit.models import AuditEvent
from apps.findings.models import Finding, ManualIssue
from apps.findings.services import create_manual_issue
from apps.tenancy.models import (
    BusinessUnit,
    BusinessUnitGrant,
    MembershipRole,
    Organisation,
    OrganisationMembership,
)

pytestmark = pytest.mark.django_db
REPORTED_AT = datetime(2026, 1, 1, tzinfo=UTC)
NAIVE_REPORTED_AT = REPORTED_AT.replace(tzinfo=None)


def security_context(
    *, sensitive: bool = False
) -> tuple[Organisation, BusinessUnit, User, OrganisationMembership]:
    organisation = Organisation.objects.create(
        name=f"Org {uuid.uuid4()}", slug=f"org-{uuid.uuid4()}"
    )
    unit = BusinessUnit.objects.create(
        organisation=organisation, name="Unit", slug="unit", is_sensitive=sensitive
    )
    analyst = User.objects.create_user(username=f"analyst-{uuid.uuid4()}")
    membership = OrganisationMembership.objects.create(
        organisation=organisation, user=analyst, role=MembershipRole.SECURITY_ANALYST
    )
    analyst.is_verified = lambda: True  # type: ignore[attr-defined,method-assign]
    return organisation, unit, analyst, membership


def test_manual_issue_stays_separate_and_is_audited() -> None:
    organisation, unit, analyst, membership = security_context(sensitive=True)
    BusinessUnitGrant.objects.create(membership=membership, business_unit=unit)
    asset = Asset.objects.create(
        organisation=organisation,
        business_unit=unit,
        asset_type=AssetType.APPLICATION,
        canonical_name="checkout",
    )

    issue = create_manual_issue(
        organisation=organisation,
        reporter=analyst,
        title=" Manual access review ",
        description=" Excessive access observed ",
        reported_at=REPORTED_AT,
        business_unit=unit,
        asset=asset,
    )

    assert ManualIssue.objects.get() == issue
    assert Finding.objects.exists() is False
    assert issue.title == "Manual access review"
    assert AuditEvent.objects.get(action="manual_issue.created").object_id == str(issue.id)


def test_manual_issue_requires_verified_security_role() -> None:
    organisation, unit, analyst, membership = security_context()
    analyst.is_verified = lambda: False  # type: ignore[attr-defined,method-assign]

    with pytest.raises(PermissionError, match="MFA-verified"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title="Issue",
            description="Description",
            reported_at=REPORTED_AT,
            business_unit=unit,
        )


def test_manual_issue_rejects_cross_organisation_scope_and_empty_content() -> None:
    organisation, _unit, analyst, _membership = security_context()
    other = Organisation.objects.create(name="Other", slug="other-manual")
    other_unit = BusinessUnit.objects.create(organisation=other, name="Other", slug="other")

    with pytest.raises(ValueError, match="title and description"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title=" ",
            description="Description",
            reported_at=REPORTED_AT,
        )
    with pytest.raises(ValueError, match="Business unit"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title="Issue",
            description="Description",
            reported_at=REPORTED_AT,
            business_unit=other_unit,
        )


def test_manual_issue_rejects_naive_time_cross_org_asset_and_unit_mismatch() -> None:
    organisation, unit, analyst, _membership = security_context()
    other = Organisation.objects.create(name="Other asset org", slug="other-asset-org")
    other_asset = Asset.objects.create(
        organisation=other, asset_type=AssetType.HOST, canonical_name="other-host"
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title="Issue",
            description="Description",
            reported_at=NAIVE_REPORTED_AT,
        )
    with pytest.raises(ValueError, match="Asset and issue organisations"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title="Issue",
            description="Description",
            reported_at=REPORTED_AT,
            asset=other_asset,
        )

    another_unit = BusinessUnit.objects.create(
        organisation=organisation, name="Another", slug="another"
    )
    BusinessUnitGrant.objects.create(membership=membership, business_unit=another_unit)
    scoped_asset = Asset.objects.create(
        organisation=organisation,
        business_unit=unit,
        asset_type=AssetType.HOST,
        canonical_name="scoped-host",
    )
    with pytest.raises(ValueError, match="business units"):
        create_manual_issue(
            organisation=organisation,
            reporter=analyst,
            title="Issue",
            description="Description",
            reported_at=REPORTED_AT,
            business_unit=another_unit,
            asset=scoped_asset,
        )
