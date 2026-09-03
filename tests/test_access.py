# SPDX-License-Identifier: Apache-2.0
"""Positive and negative tests for scoped business-unit access."""

import pytest
from django.test import Client

from apps.accounts.access import can_perform_privileged_action
from apps.accounts.models import User
from apps.tenancy.access import can_access_business_unit
from apps.tenancy.models import (
    BusinessUnit,
    BusinessUnitGrant,
    MembershipRole,
    Organisation,
    OrganisationMembership,
)
from apps.tenancy.services import grant_business_unit, revoke_business_unit, set_membership_active

pytestmark = pytest.mark.django_db


def create_scope(
    *, role: str, sensitive: bool = False
) -> tuple[User, OrganisationMembership, BusinessUnit]:
    user = User.objects.create_user(username=f"user-{role}", password="test-only-password")
    organisation = Organisation.objects.create(name=f"Org {role}", slug=f"org-{role}")
    unit = BusinessUnit.objects.create(
        organisation=organisation, name="Unit", slug="unit", is_sensitive=sensitive
    )
    membership = OrganisationMembership.objects.create(
        organisation=organisation, user=user, role=role
    )
    return user, membership, unit


def test_senior_analyst_has_non_sensitive_organisation_scope() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SENIOR_SECURITY_ANALYST)

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert decision.allowed is True
    assert decision.reason == "organisation_wide_role"


def test_sensitive_unit_denies_global_role_without_explicit_grant() -> None:
    user, membership, unit = create_scope(
        role=MembershipRole.SENIOR_SECURITY_ANALYST, sensitive=True
    )

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert decision.allowed is False
    assert decision.reason == "sensitive_denied"


def test_explicit_grant_allows_sensitive_unit() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ANALYST, sensitive=True)
    BusinessUnitGrant.objects.create(membership=membership, business_unit=unit)

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert decision.allowed is True
    assert decision.reason == "explicit_sensitive_grant"


def test_membership_in_another_organisation_never_grants_access() -> None:
    user, membership, _unit = create_scope(role=MembershipRole.SECURITY_ADMIN)
    other = Organisation.objects.create(name="Other", slug="other")
    other_unit = BusinessUnit.objects.create(organisation=other, name="Other", slug="other")

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=other_unit
    )

    assert decision.allowed is False
    assert decision.reason == "different_organisation"


def test_inactive_membership_does_not_grant_access() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ADMIN)
    membership.is_active = False
    membership.save(update_fields=("is_active",))

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert decision.allowed is False
    assert decision.reason == "no_active_membership"


def test_privileged_role_requires_verified_mfa() -> None:
    user, _membership, _unit = create_scope(role=MembershipRole.SECURITY_ANALYST)
    user.is_verified = lambda: False  # type: ignore[attr-defined,method-assign]

    assert can_perform_privileged_action(user=user) is False

    user.is_verified = lambda: True  # type: ignore[attr-defined,method-assign]
    assert can_perform_privileged_action(user=user) is True


def test_delivery_owner_is_not_a_privileged_role_even_with_mfa() -> None:
    user, _membership, _unit = create_scope(role=MembershipRole.DELIVERY_OWNER)
    user.is_verified = lambda: True  # type: ignore[attr-defined,method-assign]

    assert can_perform_privileged_action(user=user) is False


def test_inactive_user_is_denied_before_membership_lookup() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ADMIN)
    user.is_active = False
    user.save(update_fields=("is_active",))

    decision = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert decision.allowed is False
    assert decision.reason == "inactive_or_unauthenticated"
    assert can_perform_privileged_action(user=user) is False


def test_ordinary_analyst_needs_explicit_non_sensitive_grant() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ANALYST)

    denied = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )
    BusinessUnitGrant.objects.create(membership=membership, business_unit=unit)
    allowed = can_access_business_unit(
        user=user, organisation_id=membership.organisation_id, business_unit=unit
    )

    assert denied.reason == "business_unit_not_granted"
    assert denied.allowed is False
    assert allowed.reason == "explicit_business_unit_grant"
    assert allowed.allowed is True


def test_grant_and_revoke_invalidate_existing_authorization_version() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ANALYST)
    original = user.authorization_version

    grant_business_unit(membership=membership, business_unit=unit)
    after_grant = user.authorization_version
    revoked = revoke_business_unit(membership=membership, business_unit=unit)

    assert after_grant == original + 1
    assert revoked is True
    assert user.authorization_version == original + 2


def test_cross_organisation_grant_is_rejected() -> None:
    _user, membership, _unit = create_scope(role=MembershipRole.SECURITY_ANALYST)
    other = Organisation.objects.create(name="Grant Other", slug="grant-other")
    other_unit = BusinessUnit.objects.create(organisation=other, name="Other", slug="other")

    with pytest.raises(ValueError, match="same organisation"):
        grant_business_unit(membership=membership, business_unit=other_unit)


def test_deactivating_membership_invalidates_existing_session(client: Client) -> None:
    user, membership, _unit = create_scope(role=MembershipRole.DELIVERY_OWNER)
    client.force_login(user)
    session = client.session
    session["authorization_version"] = user.authorization_version
    session.save()

    set_membership_active(membership=membership, active=False)
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/accounts/login/")


def test_repeating_membership_and_grant_operations_are_noops() -> None:
    user, membership, unit = create_scope(role=MembershipRole.SECURITY_ANALYST)
    grant_business_unit(membership=membership, business_unit=unit)
    version = user.authorization_version

    grant_business_unit(membership=membership, business_unit=unit)
    missing_revoke = revoke_business_unit(
        membership=membership,
        business_unit=BusinessUnit.objects.create(
            organisation=membership.organisation, name="Missing", slug="missing"
        ),
    )
    set_membership_active(membership=membership, active=True)

    user.refresh_from_db()
    assert user.authorization_version == version
    assert missing_revoke is False
