# SPDX-License-Identifier: Apache-2.0
"""Retry-safe raw record and normalized finding provenance tests."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from apps.assets.models import Asset, AssetType
from apps.findings.models import (
    Finding,
    FindingIdentifier,
    FindingStatus,
    IdentifierType,
    ProviderSeverity,
)
from apps.findings.services import NormalizedFinding, upsert_finding
from apps.integrations.models import (
    ImportRun,
    ImportStatus,
    RawSourceRecord,
    SourceAccount,
    SourceKind,
)
from apps.integrations.services import canonical_payload_hash, store_raw_record
from apps.tenancy.models import Organisation

pytestmark = pytest.mark.django_db(transaction=True)


def source_context() -> tuple[Organisation, SourceAccount, ImportRun]:
    organisation = Organisation.objects.create(
        name=f"Org {uuid.uuid4()}", slug=f"org-{uuid.uuid4()}"
    )
    source = SourceAccount.objects.create(
        organisation=organisation, kind=SourceKind.CSV, name="Fixture source"
    )
    run = ImportRun.objects.create(
        organisation=organisation,
        source_account=source,
        correlation_id=uuid.uuid4(),
        status=ImportStatus.RUNNING,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return organisation, source, run


def test_payload_hash_is_stable_across_key_order() -> None:
    assert canonical_payload_hash({"b": 2, "a": 1}) == canonical_payload_hash({"a": 1, "b": 2})


def test_store_raw_record_is_idempotent_and_versions_changed_payload() -> None:
    _organisation, source, run = source_context()
    observed = datetime(2026, 1, 1, tzinfo=UTC)

    first = store_raw_record(
        source_account=source,
        import_run=run,
        external_id=" finding-1 ",
        observed_at=observed,
        payload={"state": "active"},
    )
    retry = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="finding-1",
        observed_at=observed,
        payload={"state": "active"},
    )
    changed = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="finding-1",
        observed_at=observed + timedelta(days=1),
        payload={"state": "resolved"},
    )

    assert first.created is True
    assert retry.created is False
    assert retry.record.id == first.record.id
    assert changed.created is True
    assert RawSourceRecord.objects.count() == 2


def test_raw_record_cannot_be_edited() -> None:
    _organisation, source, run = source_context()
    stored = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="immutable",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload={"value": 1},
    ).record
    stored.payload = {"value": 2}

    with pytest.raises(TypeError, match="immutable"):
        stored.save()


def test_store_raw_record_rejects_mismatched_run_and_empty_identity() -> None:
    organisation, source, _run = source_context()
    other = SourceAccount.objects.create(
        organisation=organisation, kind=SourceKind.CSV, name="Other source"
    )
    other_run = ImportRun.objects.create(
        organisation=organisation,
        source_account=other,
        correlation_id=uuid.uuid4(),
        status=ImportStatus.RUNNING,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="do not match"):
        store_raw_record(
            source_account=source,
            import_run=other_run,
            external_id="one",
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            payload={},
        )
    with pytest.raises(ValueError, match="stable external"):
        store_raw_record(
            source_account=other,
            import_run=other_run,
            external_id=" ",
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            payload={},
        )


def test_finding_upsert_preserves_first_seen_and_all_raw_versions() -> None:
    organisation, source, run = source_context()
    asset = Asset.objects.create(
        organisation=organisation,
        asset_type=AssetType.HOST,
        canonical_name="host.example.test",
    )
    day_one = datetime(2026, 1, 1, tzinfo=UTC)
    raw_one = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="finding-1",
        observed_at=day_one,
        payload={"state": "active"},
    ).record
    envelope_one = NormalizedFinding(
        external_id="finding-1",
        title="Old Apache",
        description="Synthetic exposure",
        remediation="Upgrade Apache",
        provider_severity=ProviderSeverity.HIGH,
        status=FindingStatus.ACTIVE,
        observed_at=day_one,
        identifiers=((IdentifierType.CVE, "cve-2099-0001"),),
    )

    created = upsert_finding(
        source_account=source, raw_record=raw_one, asset=asset, envelope=envelope_one
    )
    retry = upsert_finding(
        source_account=source, raw_record=raw_one, asset=asset, envelope=envelope_one
    )
    day_two = day_one + timedelta(days=1)
    raw_two = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="finding-1",
        observed_at=day_two,
        payload={"state": "resolved"},
    ).record
    updated = upsert_finding(
        source_account=source,
        raw_record=raw_two,
        asset=asset,
        envelope=NormalizedFinding(
            **{
                **envelope_one.__dict__,
                "status": FindingStatus.RESOLVED,
                "observed_at": day_two,
            }
        ),
    )

    updated.finding.refresh_from_db()
    assert created.created is True
    assert retry.changed is False
    assert updated.created is False
    assert updated.changed is True
    assert updated.finding.first_observed_at == day_one
    assert updated.finding.last_observed_at == day_two
    assert updated.finding.current_raw_record == raw_two
    assert RawSourceRecord.objects.filter(external_id="finding-1").count() == 2
    assert FindingIdentifier.objects.get(finding=updated.finding).value == "CVE-2099-0001"


def test_database_rejects_reversed_observation_range() -> None:
    organisation, source, run = source_context()
    raw = store_raw_record(
        source_account=source,
        import_run=run,
        external_id="bad-time",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload={},
    ).record
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Finding.objects.create(
                organisation=organisation,
                source_account=source,
                external_id="bad-time",
                current_raw_record=raw,
                title="Bad range",
                first_observed_at=datetime(2026, 1, 2, tzinfo=UTC),
                last_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
