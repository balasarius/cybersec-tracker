# SPDX-License-Identifier: Apache-2.0
"""Source accounts, imports, and original provider records."""

import uuid
from typing import Any

from django.db import models

from apps.tenancy.models import Organisation


class SourceKind(models.TextChoices):
    SECURITY_SCORECARD = "security_scorecard", "SecurityScorecard"
    WIZ = "wiz", "Wiz"
    TENABLE = "tenable", "Nessus / Tenable"
    CSV = "csv", "CSV"


class SourceAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    kind = models.CharField(max_length=40, choices=SourceKind.choices)
    name = models.CharField(max_length=200)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "name"), name="integrations_source_org_name_unique"
            )
        ]


class ImportStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    PARTIAL = "partial", "Partially succeeded"
    FAILED = "failed", "Failed"


class ImportRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    source_account = models.ForeignKey(SourceAccount, on_delete=models.PROTECT)
    correlation_id = models.UUIDField()
    status = models.CharField(max_length=20, choices=ImportStatus.choices)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    checkpoint_before = models.TextField(blank=True)
    checkpoint_after = models.TextField(blank=True)


class RawSourceRecord(models.Model):
    """An immutable provider payload version retained for provenance and replay."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    source_account = models.ForeignKey(SourceAccount, on_delete=models.PROTECT)
    import_run = models.ForeignKey(ImportRun, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=500)
    content_sha256 = models.CharField(max_length=64)
    observed_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_account", "external_id", "content_sha256"),
                name="integrations_raw_version_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("organisation", "source_account", "external_id"),
                name="integrations_raw_lookup_idx",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise TypeError("Raw source records are immutable")
        super().save(*args, **kwargs)
