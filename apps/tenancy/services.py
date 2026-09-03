# SPDX-License-Identifier: Apache-2.0
"""Auditable-ready membership operations with session invalidation."""

from django.db import transaction

from apps.accounts.services import bump_authorization_version
from apps.tenancy.models import (
    BusinessUnit,
    BusinessUnitGrant,
    MembershipRole,
    OrganisationMembership,
)


@transaction.atomic
def grant_business_unit(
    *, membership: OrganisationMembership, business_unit: BusinessUnit
) -> BusinessUnitGrant:
    if membership.organisation_id != business_unit.organisation_id:
        raise ValueError("Membership and business unit must belong to the same organisation")
    grant, created = BusinessUnitGrant.objects.get_or_create(
        membership=membership, business_unit=business_unit
    )
    if created:
        bump_authorization_version(user=membership.user)
    return grant


@transaction.atomic
def revoke_business_unit(
    *, membership: OrganisationMembership, business_unit: BusinessUnit
) -> bool:
    deleted, _ = BusinessUnitGrant.objects.filter(
        membership=membership, business_unit=business_unit
    ).delete()
    if deleted:
        bump_authorization_version(user=membership.user)
    return bool(deleted)


@transaction.atomic
def set_membership_active(*, membership: OrganisationMembership, active: bool) -> None:
    if membership.is_active == active:
        return
    membership.is_active = active
    membership.save(update_fields=("is_active",))
    bump_authorization_version(user=membership.user)


@transaction.atomic
def change_membership_role(*, membership: OrganisationMembership, role: str) -> None:
    if role not in MembershipRole.values:
        raise ValueError("Unknown membership role")
    if membership.role == role:
        return
    membership.role = role
    membership.save(update_fields=("role",))
    bump_authorization_version(user=membership.user)
