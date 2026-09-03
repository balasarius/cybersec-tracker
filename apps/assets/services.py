# SPDX-License-Identifier: Apache-2.0
"""Explainable asset identity resolution and analyst decisions."""

import ipaddress
import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.accounts.access import can_perform_privileged_action
from apps.accounts.models import User
from apps.assets.models import (
    AliasType,
    Asset,
    AssetAlias,
    AssetResolutionCase,
    ResolutionStatus,
)
from apps.audit.services import append_event
from apps.integrations.models import SourceAccount
from apps.tenancy.access import can_access_business_unit

MAC_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class ResolutionKind(StrEnum):
    EXACT = "exact"
    REVIEW = "review"
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class AssetResolution:
    kind: ResolutionKind
    normalized_value: str
    asset: Asset | None
    review_case: AssetResolutionCase | None
    candidate_ids: tuple[UUID, ...]
    explanation: str


def normalize_alias(*, alias_type: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Asset identity cannot be empty")
    if alias_type == AliasType.FQDN:
        return normalized.lower().rstrip(".")
    if alias_type == AliasType.IP:
        return str(ipaddress.ip_address(normalized))
    if alias_type == AliasType.MAC:
        compact = re.sub(r"[:-]", "", normalized).lower()
        if not MAC_PATTERN.fullmatch(compact):
            raise ValueError("Invalid MAC address")
        return compact
    if alias_type not in AliasType.values:
        raise ValueError("Unknown asset alias type")
    return normalized


@transaction.atomic
def resolve_asset(
    *, source_account: SourceAccount, alias_type: str, value: str, context: str = ""
) -> AssetResolution:
    normalized = normalize_alias(alias_type=alias_type, value=value)
    candidates = list(
        Asset.objects.filter(
            organisation_id=source_account.organisation_id,
            aliases__alias_type=alias_type,
            aliases__normalized_value=normalized,
            aliases__context=context.strip(),
            is_active=True,
        ).distinct()
    )
    candidate_ids = tuple(asset.id for asset in candidates)
    if len(candidates) == 1 and alias_type != AliasType.IP:
        return AssetResolution(
            ResolutionKind.EXACT,
            normalized,
            candidates[0],
            None,
            candidate_ids,
            "One active asset matched a strong normalized alias in the same "
            "organisation and context",
        )
    if not candidates:
        return AssetResolution(
            ResolutionKind.UNMATCHED,
            normalized,
            None,
            None,
            (),
            "No active asset matched; analyst creation or alias assignment is required",
        )
    review_case, _ = AssetResolutionCase.objects.get_or_create(
        source_account=source_account,
        alias_type=alias_type,
        normalized_value=normalized,
        context=context.strip(),
        status=ResolutionStatus.OPEN,
        defaults={
            "organisation_id": source_account.organisation_id,
            "candidate_asset_ids": [str(candidate_id) for candidate_id in candidate_ids],
        },
    )
    explanation = (
        "IP address is a weak identity and requires analyst review"
        if alias_type == AliasType.IP
        else "Multiple active assets matched and require analyst review"
    )
    return AssetResolution(
        ResolutionKind.REVIEW,
        normalized,
        None,
        review_case,
        candidate_ids,
        explanation,
    )


@transaction.atomic
def approve_asset_resolution(
    *, review_case: AssetResolutionCase, asset: Asset, analyst: User, reason: str
) -> AssetAlias:
    """Resolve an ambiguity without deleting the case or competing aliases."""
    if review_case.status != ResolutionStatus.OPEN:
        raise ValueError("Asset resolution case is no longer open")
    if review_case.organisation_id != asset.organisation_id:
        raise ValueError("Resolution case and asset organisations do not match")
    if not reason.strip():
        raise ValueError("A resolution reason is required")
    if not can_perform_privileged_action(user=analyst):
        raise PermissionError("MFA-verified Security access is required")
    if asset.business_unit is not None:
        access = can_access_business_unit(
            user=analyst,
            organisation_id=asset.organisation_id,
            business_unit=asset.business_unit,
        )
        if not access.allowed:
            raise PermissionError("Analyst cannot access the selected asset")
    now = timezone.now()
    alias, _ = AssetAlias.objects.get_or_create(
        organisation_id=asset.organisation_id,
        asset=asset,
        alias_type=review_case.alias_type,
        normalized_value=review_case.normalized_value,
        context=review_case.context,
        defaults={
            "source_account": review_case.source_account,
            "first_seen_at": now,
            "last_seen_at": now,
        },
    )
    review_case.status = ResolutionStatus.RESOLVED
    review_case.resolved_at = now
    review_case.resolved_by = analyst
    review_case.resolution_reason = reason.strip()
    review_case.save(update_fields=("status", "resolved_at", "resolved_by", "resolution_reason"))
    append_event(
        organisation_id=asset.organisation_id,
        action="asset.resolution_approved",
        object_type="asset_resolution_case",
        object_id=str(review_case.id),
        actor=analyst,
        actor_label=analyst.get_username(),
        reason=reason.strip(),
        data={"asset_id": str(asset.id), "alias_type": review_case.alias_type},
    )
    return alias
