# SPDX-License-Identifier: Apache-2.0
"""Transactional operations for appending and verifying audit events."""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.context import correlation_id as current_correlation_id
from apps.audit.models import AuditEvent, AuditHead
from apps.tenancy.models import Organisation

SENSITIVE_KEYS = {"authorization", "cookie", "password", "secret", "token"}


def redact(value: Any) -> Any:
    """Recursively redact values whose field name indicates authentication material."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@transaction.atomic
def append_event(
    *,
    organisation: Organisation,
    action: str,
    object_type: str,
    object_id: str,
    actor: User | None,
    actor_label: str,
    reason: str = "",
    data: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
    correlation_id: uuid.UUID | None = None,
) -> AuditEvent:
    """Append one deterministic event while holding the organisation chain lock."""
    head, _ = AuditHead.objects.select_for_update().get_or_create(organisation=organisation)
    timestamp = occurred_at or timezone.now()
    correlation = correlation_id or current_correlation_id.get() or uuid.uuid4()
    sequence = head.sequence + 1
    safe_data = redact(data or {})
    content = {
        "organisation_id": str(organisation.id),
        "sequence": sequence,
        "occurred_at": timestamp.isoformat(),
        "correlation_id": str(correlation),
        "actor_id": str(actor.id) if actor else None,
        "actor_label": actor_label,
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "reason": reason,
        "data": safe_data,
        "previous_hash": head.event_hash,
    }
    event = AuditEvent.objects.create(
        organisation=organisation,
        sequence=sequence,
        occurred_at=timestamp,
        correlation_id=correlation,
        actor=actor,
        actor_label=actor_label,
        action=action,
        object_type=object_type,
        object_id=object_id,
        reason=reason,
        data=safe_data,
        previous_hash=head.event_hash,
        event_hash=_digest(content),
    )
    head.sequence = sequence
    head.event_hash = event.event_hash
    head.save(update_fields=("sequence", "event_hash"))
    return event


@dataclass(frozen=True)
class ChainVerification:
    valid: bool
    checked: int
    first_invalid_sequence: int | None = None


def verify_chain(*, organisation: Organisation) -> ChainVerification:
    previous_hash = "0" * 64
    checked = 0
    for event in AuditEvent.objects.filter(organisation=organisation).order_by("sequence"):
        content = {
            "organisation_id": str(organisation.id),
            "sequence": event.sequence,
            "occurred_at": event.occurred_at.isoformat(),
            "correlation_id": str(event.correlation_id),
            "actor_id": str(event.actor_id) if event.actor_id else None,
            "actor_label": event.actor_label,
            "action": event.action,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "reason": event.reason,
            "data": event.data,
            "previous_hash": previous_hash,
        }
        checked += 1
        if event.previous_hash != previous_hash or event.event_hash != _digest(content):
            return ChainVerification(False, checked, event.sequence)
        previous_hash = event.event_hash
    return ChainVerification(True, checked)
