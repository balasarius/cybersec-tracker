# SPDX-License-Identifier: Apache-2.0
"""Append-only, hash-chained business audit records."""

import uuid
from typing import Any

from django.conf import settings
from django.db import models

from apps.tenancy.models import Organisation


class AuditEventQuerySet(models.QuerySet["AuditEvent"]):
    def update(self, **kwargs: object) -> int:
        raise TypeError("Audit events are append-only")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise TypeError("Audit events are append-only")


class AuditHead(models.Model):
    """Lockable per-organisation pointer used to serialize audit appends."""

    organisation = models.OneToOneField(Organisation, on_delete=models.PROTECT, primary_key=True)
    sequence = models.PositiveBigIntegerField(default=0)
    event_hash = models.CharField(max_length=64, default="0" * 64)


class AuditEvent(models.Model):
    """Immutable event; application code may only create through the audit service."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    sequence = models.PositiveBigIntegerField()
    occurred_at = models.DateTimeField()
    correlation_id = models.UUIDField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    actor_label = models.CharField(max_length=255)
    action = models.CharField(max_length=150)
    object_type = models.CharField(max_length=150)
    object_id = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    data = models.JSONField(default=dict)
    previous_hash = models.CharField(max_length=64)
    event_hash = models.CharField(max_length=64)
    objects = AuditEventQuerySet.as_manager()

    class Meta:
        ordering = ("organisation_id", "sequence")
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "sequence"), name="audit_event_org_sequence_unique"
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise TypeError("Audit events are append-only")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise TypeError("Audit events are append-only")
