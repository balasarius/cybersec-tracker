# SPDX-License-Identifier: Apache-2.0
"""Organisation, business-unit, team, and scoped membership records."""

import uuid

from django.conf import settings
from django.db import models


class Organisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BusinessUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    is_sensitive = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "slug"), name="tenancy_unit_org_slug_unique"
            )
        ]


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "slug"), name="tenancy_team_org_slug_unique"
            )
        ]


class MembershipRole(models.TextChoices):
    SECURITY_ADMIN = "security_admin", "Security administrator"
    SENIOR_SECURITY_ANALYST = "senior_security_analyst", "Senior security analyst"
    SECURITY_ANALYST = "security_analyst", "Security analyst"
    RISK_EXECUTIVE = "risk_executive", "Risk executive"
    DELIVERY_OWNER = "delivery_owner", "Delivery owner"
    AUDITOR = "auditor", "Auditor"


class OrganisationMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=40, choices=MembershipRole.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organisation", "user", "role"), name="tenancy_org_user_role_unique"
            )
        ]


class BusinessUnitGrant(models.Model):
    """Explicit scope for analysts/auditors and the only route into sensitive units."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(
        OrganisationMembership, on_delete=models.CASCADE, related_name="business_unit_grants"
    )
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("membership", "business_unit"), name="tenancy_membership_unit_unique"
            )
        ]


class TeamMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(OrganisationMembership, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("membership", "team"), name="tenancy_membership_team_unique"
            )
        ]
