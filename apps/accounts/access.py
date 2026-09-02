# SPDX-License-Identifier: Apache-2.0
"""Authentication-strength predicates for privileged domain commands."""

from apps.accounts.models import User
from apps.tenancy.models import MembershipRole, OrganisationMembership

PRIVILEGED_ROLES = {
    MembershipRole.SECURITY_ADMIN,
    MembershipRole.SENIOR_SECURITY_ANALYST,
    MembershipRole.SECURITY_ANALYST,
    MembershipRole.RISK_EXECUTIVE,
}


def has_privileged_role(*, user: User) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    return OrganisationMembership.objects.filter(
        user=user, is_active=True, role__in=PRIVILEGED_ROLES
    ).exists()


def can_perform_privileged_action(*, user: User) -> bool:
    """Require an authenticated OTP session for every privileged role."""
    if not has_privileged_role(user=user):
        return False
    is_verified = getattr(user, "is_verified", None)
    return bool(callable(is_verified) and is_verified())
