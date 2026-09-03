# SPDX-License-Identifier: Apache-2.0
"""Authentication hashing, recovery, throttling, and TOTP tests."""

import html
import re

import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core import mail
from django.test import Client, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import RecoveryCode, User
from apps.accounts.recovery import reset_mfa
from apps.accounts.services import consume_recovery_code, replace_recovery_codes
from apps.audit.models import AuditEvent
from apps.tenancy.models import MembershipRole, Organisation, OrganisationMembership

pytestmark = pytest.mark.django_db


def test_new_passwords_use_argon2id() -> None:
    user = User.objects.create_user(
        username="argon", email="argon@example.test", password="valid-pass"
    )

    assert identify_hasher(user.password).algorithm == "argon2"
    assert user.check_password("valid-pass") is True


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_does_not_disclose_unknown_account(client: Client) -> None:
    response = client.post("/accounts/password_reset/", {"email": "missing@example.test"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/accounts/password_reset/done/")
    assert mail.outbox == []


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_sends_single_use_link_for_active_account(client: Client) -> None:
    User.objects.create_user(
        username="recover", email="recover@example.test", password="valid-pass"
    )

    response = client.post("/accounts/password_reset/", {"email": "recover@example.test"})

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert re.search(r"/accounts/reset/[^/]+/[^/]+/", mail.outbox[0].body)


def test_totp_device_accepts_current_token_once_window_is_valid() -> None:
    user = User.objects.create_user(username="totp", email="totp@example.test")
    device = TOTPDevice.objects.create(user=user, name="primary", confirmed=True)
    token = totp(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift,
    )

    assert device.verify_token(token) is True


@override_settings(AXES_FAILURE_LIMIT=2)
def test_repeated_login_failure_is_locked(client: Client) -> None:
    User.objects.create_user(username="locked", password="valid-pass")
    login = "/accounts/login/"

    first = client.post(login, {"username": "locked", "password": "wrong"})
    second = client.post(login, {"username": "locked", "password": "wrong"})
    locked = client.post(login, {"username": "locked", "password": "valid-pass"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert locked.status_code == 429


def create_privileged_user(*, username: str) -> User:
    user = User.objects.create_user(username=username, password="valid-pass")
    organisation = Organisation.objects.create(name=f"Org {username}", slug=f"org-{username}")
    OrganisationMembership.objects.create(
        organisation=organisation, user=user, role=MembershipRole.SECURITY_ANALYST
    )
    return user


def test_privileged_password_login_requires_enrollment_when_no_device(client: Client) -> None:
    create_privileged_user(username="enrol")

    response = client.post("/accounts/login/", {"username": "enrol", "password": "valid-pass"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/accounts/mfa/setup/")


def test_privileged_password_login_requires_second_factor(client: Client) -> None:
    user = create_privileged_user(username="second-factor")
    device = TOTPDevice.objects.create(user=user, name="primary", confirmed=True)
    token = totp(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift,
    )

    password_response = client.post(
        "/accounts/login/", {"username": "second-factor", "password": "valid-pass"}
    )
    verify_response = client.post("/accounts/mfa/verify/", {"token": str(token)})

    assert password_response.status_code == 302
    assert password_response.headers["Location"].endswith("/accounts/mfa/verify/")
    assert verify_response.status_code == 302
    assert verify_response.headers["Location"].endswith("/health/live")
    assert client.session.get("otp_device_id") == device.persistent_id


def test_mfa_preauth_session_is_discarded_after_bounded_failures(client: Client) -> None:
    user = create_privileged_user(username="mfa-bounded")
    TOTPDevice.objects.create(user=user, name="primary", confirmed=True)
    client.post("/accounts/login/", {"username": "mfa-bounded", "password": "valid-pass"})

    responses = [client.post("/accounts/mfa/verify/", {"token": "000000"}) for _ in range(5)]

    assert all(response.status_code == 200 for response in responses[:4])
    assert responses[-1].status_code == 302
    assert responses[-1].headers["Location"].endswith("/accounts/login/")
    assert "mfa_preauth_user_id" not in client.session


def test_mfa_setup_confirms_device_and_shows_codes_once(client: Client) -> None:
    user = create_privileged_user(username="setup")
    client.force_login(user)
    session = client.session
    session["authorization_version"] = user.authorization_version
    session.save()

    start = client.post("/accounts/mfa/setup/", {"action": "start"})
    device = TOTPDevice.objects.get(user=user, confirmed=False)
    token = totp(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift,
    )
    confirm = client.post("/accounts/mfa/setup/", {"action": "confirm", "token": str(token)})

    assert start.status_code == 200
    assert html.escape(device.config_url) in start.content.decode()
    assert confirm.status_code == 200
    assert b"Save your recovery codes" in confirm.content
    assert RecoveryCode.objects.filter(user=user, used_at__isnull=True).count() == 10


def test_recovery_code_is_hashed_and_single_use() -> None:
    user = User.objects.create_user(username="recovery")

    generated = replace_recovery_codes(user=user, count=1)
    plaintext = generated.plaintext[0]
    stored = RecoveryCode.objects.get(user=user)

    assert plaintext not in stored.code_hash
    assert consume_recovery_code(user=user, candidate=plaintext) is True
    assert consume_recovery_code(user=user, candidate=plaintext) is False


@pytest.mark.parametrize("count", [0, 21])
def test_recovery_code_count_is_bounded(count: int) -> None:
    user = User.objects.create_user(username=f"bounded-{count}")

    with pytest.raises(ValueError, match="between 1 and 20"):
        replace_recovery_codes(user=user, count=count)


def test_known_user_login_failure_is_audited_without_changing_response(client: Client) -> None:
    user = create_privileged_user(username="audit-failure")

    response = client.post("/accounts/login/", {"username": "audit-failure", "password": "wrong"})

    assert response.status_code == 200
    event = AuditEvent.objects.get(action="authentication.failed")
    assert event.object_id == str(user.id)
    assert event.actor is None


def test_verified_security_admin_can_reset_another_users_mfa() -> None:
    actor = User.objects.create_user(username="recovery-admin")
    target = User.objects.create_user(username="recovery-target")
    organisation = Organisation.objects.create(name="Recovery Org", slug="recovery-org")
    OrganisationMembership.objects.create(
        organisation=organisation, user=actor, role=MembershipRole.SECURITY_ADMIN
    )
    OrganisationMembership.objects.create(
        organisation=organisation, user=target, role=MembershipRole.SECURITY_ANALYST
    )
    actor.is_verified = lambda: True  # type: ignore[attr-defined,method-assign]
    TOTPDevice.objects.create(user=target, name="primary", confirmed=True)
    replace_recovery_codes(user=target, count=2)
    original_version = target.authorization_version

    event = reset_mfa(
        organisation=organisation,
        actor=actor,
        target=target,
        reason="Identity verified by service desk",
    )

    assert TOTPDevice.objects.filter(user=target).exists() is False
    assert RecoveryCode.objects.filter(user=target).exists() is False
    assert target.authorization_version == original_version + 1
    assert event.action == "authentication.mfa_reset"
    assert event.reason == "Identity verified by service desk"


def test_mfa_reset_rejects_self_service_and_unverified_admin() -> None:
    actor = User.objects.create_user(username="recovery-denied")
    target = User.objects.create_user(username="recovery-denied-target")
    organisation = Organisation.objects.create(name="Denied Recovery", slug="denied-recovery")
    OrganisationMembership.objects.create(
        organisation=organisation, user=actor, role=MembershipRole.SECURITY_ADMIN
    )
    OrganisationMembership.objects.create(
        organisation=organisation, user=target, role=MembershipRole.SECURITY_ANALYST
    )
    actor.is_verified = lambda: False  # type: ignore[attr-defined,method-assign]

    with pytest.raises(PermissionError, match="own MFA"):
        reset_mfa(organisation=organisation, actor=actor, target=actor, reason="self")
    with pytest.raises(PermissionError, match="Verified Security administrator"):
        reset_mfa(organisation=organisation, actor=actor, target=target, reason="help")
