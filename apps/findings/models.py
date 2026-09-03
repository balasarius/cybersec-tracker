# SPDX-License-Identifier: Apache-2.0
"""Normalised provider findings and deliberately separate manual issues."""

import uuid

from django.conf import settings
from django.db import models

from apps.assets.models import Asset
from apps.integrations.models import RawSourceRecord, SourceAccount
from apps.tenancy.models import BusinessUnit, Organisation


class FindingStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    RESOLVED = "resolved", "Resolved"
    NOT_OBSERVED = "not_observed", "Not observed"
    UNKNOWN = "unknown", "Unknown"


class ProviderSeverity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    INFORMATIONAL = "informational", "Informational"
    UNKNOWN = "unknown", "Unknown"


class Finding(models.Model):
    """Current normalized state for one stable provider finding identity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    source_account = models.ForeignKey(SourceAccount, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=500)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT)
    current_raw_record = models.ForeignKey(RawSourceRecord, on_delete=models.PROTECT)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    remediation = models.TextField(blank=True)
    provider_severity = models.CharField(
        max_length=20, choices=ProviderSeverity.choices, default="unknown"
    )
    status = models.CharField(max_length=20, choices=FindingStatus.choices, default="active")
    first_observed_at = models.DateTimeField()
    last_observed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_account", "external_id"), name="findings_source_external_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(last_observed_at__gte=models.F("first_observed_at")),
                name="findings_observation_order_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("organisation", "status", "last_observed_at"),
                name="findings_org_status_seen_idx",
            )
        ]


class IdentifierType(models.TextChoices):
    CVE = "cve", "CVE"
    CWE = "cwe", "CWE"
    PROVIDER_RULE = "provider_rule", "Provider rule"


class FindingIdentifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    finding = models.ForeignKey(Finding, on_delete=models.CASCADE, related_name="identifiers")
    identifier_type = models.CharField(max_length=30, choices=IdentifierType.choices)
    value = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("finding", "identifier_type", "value"),
                name="findings_identifier_unique",
            )
        ]


class ManualIssue(models.Model):
    """A human-entered concern that remains separate unless an analyst merges it later."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    business_unit = models.ForeignKey(BusinessUnit, null=True, blank=True, on_delete=models.PROTECT)
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=500)
    description = models.TextField()
    remediation = models.TextField(blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reported_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
