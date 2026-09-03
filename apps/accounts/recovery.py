# SPDX-License-Identifier: Apache-2.0
"""Administrator-assisted MFA recovery domain operation."""

from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.access import can_perform_privileged_action
from apps.accounts.models import RecoveryCode, User
from apps.accounts.services import bump_authorization_version
from apps.audit.models import AuditEvent
from apps.audit.services import append_event
from apps.tenancy.models import MembershipRole, Organisation, OrganisationMembership


@transaction.atomic
def reset_mfa(*, organisation: Organisation, actor: User, target: User, reason: str) -> AuditEvent:
    """Remove a locked-out user's factors under strict, audited controls."""
    if actor == target:
        raise PermissionError("Administrators cannot reset their own MFA")
    if not reason.strip():
        raise ValueError("A recovery reason is required")
    actor_is_admin = OrganisationMembership.objects.filter(
        organisation=organisation,
        user=actor,
        role=MembershipRole.SECURITY_ADMIN,
        is_active=True,
    ).exists()
    target_is_member = OrganisationMembership.objects.filter(
        organisation=organisation, user=target, is_active=True
    ).exists()
    if not actor_is_admin or not target_is_member or not can_perform_privileged_action(user=actor):
        raise PermissionError("Verified Security administrator access is required")

    TOTPDevice.objects.filter(user=target).delete()
    RecoveryCode.objects.filter(user=target).delete()
    bump_authorization_version(user=target)
    return append_event(
        organisation=organisation,
        action="authentication.mfa_reset",
        object_type="user",
        object_id=str(target.id),
        actor=actor,
        actor_label=actor.get_username(),
        reason=reason,
    )
