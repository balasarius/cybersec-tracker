# SPDX-License-Identifier: Apache-2.0
"""Organisation-scoped authentication audit orchestration."""

from apps.accounts.models import User
from apps.audit.services import append_event
from apps.tenancy.models import OrganisationMembership


def record_authentication_event(*, user: User, action: str) -> None:
    """Record one event per active organisation without changing the client response."""
    organisation_ids = (
        OrganisationMembership.objects.filter(user=user, is_active=True)
        .values_list("organisation_id", flat=True)
        .distinct()
    )
    for organisation_id in organisation_ids:
        append_event(
            organisation_id=organisation_id,
            action=action,
            object_type="user",
            object_id=str(user.id),
            actor=user if action != "authentication.failed" else None,
            actor_label=user.get_username(),
        )
