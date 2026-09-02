# SPDX-License-Identifier: Apache-2.0
"""Explicit, deny-by-default business-unit access decisions."""

from dataclasses import dataclass
from uuid import UUID

from apps.accounts.models import User
from apps.tenancy.models import BusinessUnit, MembershipRole, OrganisationMembership

GLOBAL_SECURITY_ROLES = {
    MembershipRole.SECURITY_ADMIN,
    MembershipRole.SENIOR_SECURITY_ANALYST,
    MembershipRole.RISK_EXECUTIVE,
}


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str


def can_access_business_unit(
    *, user: User, organisation_id: UUID, business_unit: BusinessUnit
) -> AccessDecision:
    """Decide access without treating global scope as access to sensitive units."""
    if not user.is_authenticated or not user.is_active:
        return AccessDecision(False, "inactive_or_unauthenticated")
    if business_unit.organisation_id != organisation_id:
        return AccessDecision(False, "different_organisation")

    memberships = OrganisationMembership.objects.filter(
        user=user, organisation_id=organisation_id, is_active=True
    ).prefetch_related("business_unit_grants")
    if not memberships:
        return AccessDecision(False, "no_active_membership")

    explicit = any(
        grant.business_unit_id == business_unit.id
        for membership in memberships
        for grant in membership.business_unit_grants.all()
    )
    if business_unit.is_sensitive:
        return AccessDecision(
            explicit, "explicit_sensitive_grant" if explicit else "sensitive_denied"
        )
    if explicit:
        return AccessDecision(True, "explicit_business_unit_grant")
    if any(membership.role in GLOBAL_SECURITY_ROLES for membership in memberships):
        return AccessDecision(True, "organisation_wide_role")
    return AccessDecision(False, "business_unit_not_granted")
