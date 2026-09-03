# SPDX-License-Identifier: Apache-2.0
"""Canonical assets, source aliases, and ambiguity review cases."""

import uuid

from django.conf import settings
from django.db import models

from apps.integrations.models import SourceAccount
from apps.tenancy.models import BusinessUnit, Organisation


class AssetType(models.TextChoices):
    HOST = "host", "Host"
    CLOUD_RESOURCE = "cloud_resource", "Cloud resource"
    APPLICATION = "application", "Application"
    REPOSITORY = "repository", "Repository"
    DOMAIN = "domain", "Domain"
    OTHER = "other", "Other"


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    business_unit = models.ForeignKey(BusinessUnit, null=True, blank=True, on_delete=models.PROTECT)
    asset_type = models.CharField(max_length=40, choices=AssetType.choices)
    canonical_name = models.CharField(max_length=500)
    environment = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "asset_type", "canonical_name", "environment"),
                name="assets_canonical_identity_unique",
            )
        ]


class AliasType(models.TextChoices):
    CLOUD_RESOURCE_ID = "cloud_resource_id", "Cloud resource ID"
    AGENT_ID = "agent_id", "Scanner agent ID"
    CMDB_ID = "cmdb_id", "CMDB ID"
    FQDN = "fqdn", "Fully qualified domain name"
    MAC = "mac", "MAC address"
    IP = "ip", "IP address"
    REPOSITORY_URL = "repository_url", "Repository URL"
    PROVIDER_ID = "provider_id", "Provider asset ID"


class AssetAlias(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="aliases")
    source_account = models.ForeignKey(
        SourceAccount, null=True, blank=True, on_delete=models.PROTECT
    )
    alias_type = models.CharField(max_length=40, choices=AliasType.choices)
    normalized_value = models.CharField(max_length=500)
    context = models.CharField(max_length=500, blank=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "alias_type", "normalized_value", "context", "asset"),
                name="assets_alias_asset_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("organisation", "alias_type", "normalized_value", "context"),
                name="assets_alias_resolution_idx",
            )
        ]


class ResolutionStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class AssetResolutionCase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    source_account = models.ForeignKey(SourceAccount, on_delete=models.PROTECT)
    alias_type = models.CharField(max_length=40, choices=AliasType.choices)
    normalized_value = models.CharField(max_length=500)
    context = models.CharField(max_length=500, blank=True)
    candidate_asset_ids = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=ResolutionStatus.choices, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    resolution_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source_account", "alias_type", "normalized_value", "context"),
                condition=models.Q(status="open"),
                name="assets_resolution_open_unique",
            )
        ]
