# SPDX-License-Identifier: Apache-2.0
"""Authentication hashing, recovery, throttling, and TOTP tests."""

import re

import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core import mail
from django.test import Client, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User

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
