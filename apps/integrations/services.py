# SPDX-License-Identifier: Apache-2.0
"""Retry-safe source-record persistence operations."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.integrations.models import ImportRun, RawSourceRecord, SourceAccount


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StoredRawRecord:
    record: RawSourceRecord
    created: bool


@transaction.atomic
def store_raw_record(
    *,
    source_account: SourceAccount,
    import_run: ImportRun,
    external_id: str,
    observed_at: datetime,
    payload: dict[str, Any],
) -> StoredRawRecord:
    """Persist one immutable payload version, returning the existing row on retry."""
    if import_run.source_account_id != source_account.id:
        raise ValueError("Import run and source account do not match")
    if import_run.organisation_id != source_account.organisation_id:
        raise ValueError("Import run and source account organisations do not match")
    normalized_external_id = external_id.strip()
    if not normalized_external_id:
        raise ValueError("A stable external identifier is required")
    if not timezone.is_aware(observed_at):
        raise ValueError("Observed timestamp must be timezone-aware")
    digest = canonical_payload_hash(payload)
    record, created = RawSourceRecord.objects.get_or_create(
        source_account=source_account,
        external_id=normalized_external_id,
        content_sha256=digest,
        defaults={
            "organisation_id": source_account.organisation_id,
            "import_run": import_run,
            "observed_at": observed_at,
            "payload": payload,
        },
    )
    return StoredRawRecord(record, created)
