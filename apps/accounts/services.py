# SPDX-License-Identifier: Apache-2.0
"""Explicit account security operations."""

import secrets
from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django.utils import timezone

from apps.accounts.models import RecoveryCode, User


@dataclass(frozen=True)
class GeneratedRecoveryCodes:
    plaintext: tuple[str, ...]


@transaction.atomic
def replace_recovery_codes(*, user: User, count: int = 10) -> GeneratedRecoveryCodes:
    """Replace codes and return plaintext once; only slow hashes are persisted."""
    if count < 1 or count > 20:
        raise ValueError("Recovery code count must be between 1 and 20")
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).delete()
    plaintext = tuple(secrets.token_urlsafe(12) for _ in range(count))
    RecoveryCode.objects.bulk_create(
        [RecoveryCode(user=user, code_hash=make_password(code)) for code in plaintext]
    )
    return GeneratedRecoveryCodes(plaintext)


@transaction.atomic
def consume_recovery_code(*, user: User, candidate: str) -> bool:
    """Atomically consume at most one matching unused code."""
    if not candidate or len(candidate) > 128:
        return False
    codes = RecoveryCode.objects.select_for_update().filter(user=user, used_at__isnull=True)
    for code in codes:
        if check_password(candidate, code.code_hash):
            code.used_at = timezone.now()
            code.save(update_fields=("used_at",))
            return True
    return False


def bump_authorization_version(*, user: User) -> None:
    """Invalidate existing sessions after scope or privilege changes."""
    User.objects.filter(pk=user.pk).update(
        authorization_version=models.F("authorization_version") + 1
    )
    user.refresh_from_db(fields=("authorization_version",))
