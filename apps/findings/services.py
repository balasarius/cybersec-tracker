# SPDX-License-Identifier: Apache-2.0
"""Explicit finding upsert and manual-issue creation operations."""

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from apps.accounts.access import PRIVILEGED_ROLES, can_perform_privileged_action
from apps.accounts.models import User
from apps.assets.models import Asset
from apps.audit.services import append_event
from apps.findings.models import (
    Finding,
    FindingIdentifier,
    FindingStatus,
    IdentifierType,
    ManualIssue,
    ProviderSeverity,
)
from apps.integrations.models import RawSourceRecord, SourceAccount
from apps.tenancy.access import can_access_business_unit
from apps.tenancy.models import BusinessUnit, Organisation, OrganisationMembership


@dataclass(frozen=True)
class NormalizedFinding:
    external_id: str
    title: str
    description: str
    remediation: str
    provider_severity: str
    status: str
    observed_at: datetime
    identifiers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class UpsertedFinding:
    finding: Finding
    created: bool
    changed: bool


def _validate_envelope(envelope: NormalizedFinding) -> tuple[str, str]:
    external_id = envelope.external_id.strip()
    title = envelope.title.strip()
    if not external_id or not title:
        raise ValueError("Finding external identifier and title are required")
    if envelope.provider_severity not in ProviderSeverity.values:
        raise ValueError("Unknown provider severity")
    if envelope.status not in FindingStatus.values:
        raise ValueError("Unknown finding status")
    for identifier_type, value in envelope.identifiers:
        if identifier_type not in IdentifierType.values or not value.strip():
            raise ValueError("Invalid finding identifier")
    return external_id, title


@transaction.atomic
def upsert_finding(
    *,
    source_account: SourceAccount,
    raw_record: RawSourceRecord,
    asset: Asset | None,
    envelope: NormalizedFinding,
) -> UpsertedFinding:
    """Idempotently update provider state while retaining every raw payload version."""
    external_id, title = _validate_envelope(envelope)
    if raw_record.source_account_id != source_account.id:
        raise ValueError("Raw record and source account do not match")
    if raw_record.external_id != external_id:
        raise ValueError("Raw record and normalized external identifiers do not match")
    if asset is not None and asset.organisation_id != source_account.organisation_id:
        raise ValueError("Asset and source account organisations do not match")

    finding = (
        Finding.objects.select_for_update()
        .filter(source_account=source_account, external_id=external_id)
        .first()
    )
    if finding is None:
        finding = Finding.objects.create(
            organisation_id=source_account.organisation_id,
            source_account=source_account,
            external_id=external_id,
            asset=asset,
            current_raw_record=raw_record,
            title=title,
            description=envelope.description,
            remediation=envelope.remediation,
            provider_severity=envelope.provider_severity,
            status=envelope.status,
            first_observed_at=envelope.observed_at,
            last_observed_at=envelope.observed_at,
        )
        created = changed = True
    elif finding.current_raw_record_id == raw_record.id:
        return UpsertedFinding(finding, False, False)
    else:
        finding.asset = asset
        finding.current_raw_record = raw_record
        finding.title = title
        finding.description = envelope.description
        finding.remediation = envelope.remediation
        finding.provider_severity = envelope.provider_severity
        finding.status = envelope.status
        finding.first_observed_at = min(finding.first_observed_at, envelope.observed_at)
        finding.last_observed_at = max(finding.last_observed_at, envelope.observed_at)
        finding.save()
        created, changed = False, True

    desired = {
        (
            identifier_type,
            value.strip().upper() if identifier_type == IdentifierType.CVE else value.strip(),
        )
        for identifier_type, value in envelope.identifiers
    }
    existing = set(finding.identifiers.values_list("identifier_type", "value"))
    FindingIdentifier.objects.bulk_create(
        [
            FindingIdentifier(finding=finding, identifier_type=kind, value=value)
            for kind, value in desired - existing
        ]
    )
    append_event(
        organisation_id=source_account.organisation_id,
        action="finding.created" if created else "finding.updated",
        object_type="finding",
        object_id=str(finding.id),
        actor=None,
        actor_label=f"source:{source_account.id}",
        data={
            "raw_record_id": str(raw_record.id),
            "source_account_id": str(source_account.id),
            "provider_severity": envelope.provider_severity,
            "status": envelope.status,
        },
    )
    return UpsertedFinding(finding, created, changed)


@transaction.atomic
def create_manual_issue(
    *,
    organisation: Organisation,
    reporter: User,
    title: str,
    description: str,
    reported_at: datetime,
    business_unit: BusinessUnit | None = None,
    asset: Asset | None = None,
    remediation: str = "",
) -> ManualIssue:
    """Create a manual issue without silently converting it to a provider finding."""
    if not title.strip() or not description.strip():
        raise ValueError("Manual issue title and description are required")
    membership_exists = OrganisationMembership.objects.filter(
        organisation=organisation, user=reporter, is_active=True, role__in=PRIVILEGED_ROLES
    ).exists()
    if not membership_exists or not can_perform_privileged_action(user=reporter):
        raise PermissionError("MFA-verified Security access is required")
    if business_unit is not None:
        if business_unit.organisation_id != organisation.id:
            raise ValueError("Business unit and issue organisations do not match")
        if not can_access_business_unit(
            user=reporter, organisation_id=organisation.id, business_unit=business_unit
        ).allowed:
            raise PermissionError("Reporter cannot access the business unit")
    if asset is not None and asset.organisation_id != organisation.id:
        raise ValueError("Asset and issue organisations do not match")
    issue = ManualIssue.objects.create(
        organisation=organisation,
        business_unit=business_unit,
        asset=asset,
        title=title.strip(),
        description=description.strip(),
        remediation=remediation.strip(),
        reported_by=reporter,
        reported_at=reported_at,
    )
    append_event(
        organisation=organisation,
        action="manual_issue.created",
        object_type="manual_issue",
        object_id=str(issue.id),
        actor=reporter,
        actor_label=reporter.get_username(),
        data={"business_unit_id": str(business_unit.id) if business_unit else None},
    )
    return issue
