# SPDX-License-Identifier: Apache-2.0
"""Local password, TOTP enrollment, and MFA verification views."""

import uuid

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.access import has_privileged_role
from apps.accounts.audit import record_authentication_event
from apps.accounts.forms import PasswordLoginForm, TokenForm
from apps.accounts.models import User
from apps.accounts.services import consume_recovery_code, replace_recovery_codes

PREAUTH_USER_KEY = "mfa_preauth_user_id"
MFA_ATTEMPTS_KEY = "mfa_attempts"
AUTHORIZATION_VERSION_KEY = "authorization_version"
MAX_MFA_ATTEMPTS = 5


def _record_session_version(request: HttpRequest, user: User) -> None:
    request.session[AUTHORIZATION_VERSION_KEY] = user.authorization_version


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    form = PasswordLoginForm(request=request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        assert isinstance(user, User)
        record_authentication_event(user=user, action="authentication.password_accepted")
        if has_privileged_role(user=user):
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                request.session.flush()
                request.session[PREAUTH_USER_KEY] = str(user.id)
                request.session[MFA_ATTEMPTS_KEY] = 0
                request.session.set_expiry(300)
                return redirect("mfa-verify")
            auth_login(request, user)
            _record_session_version(request, user)
            return redirect("mfa-setup")
        auth_login(request, user)
        _record_session_version(request, user)
        return redirect("health-live")
    if request.method == "POST":
        username = request.POST.get("username", "")[:150]
        failed_user = User.objects.filter(username=username).first()
        if failed_user is not None:
            record_authentication_event(user=failed_user, action="authentication.failed")
    return render(request, "registration/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_mfa(request: HttpRequest) -> HttpResponse:
    raw_user_id = request.session.get(PREAUTH_USER_KEY)
    try:
        user_id = uuid.UUID(str(raw_user_id))
    except (ValueError, AttributeError):
        return redirect("login")
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        request.session.flush()
        return redirect("login")

    form = TokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        candidate = form.cleaned_data["token"]
        devices = list(TOTPDevice.objects.filter(user=user, confirmed=True))
        device = next((item for item in devices if item.verify_token(candidate)), None)
        recovered = device is None and consume_recovery_code(user=user, candidate=candidate)
        if device is not None or recovered:
            request.session.flush()
            auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if device is None:
                device = devices[0]
            otp_login(request, device)
            _record_session_version(request, user)
            record_authentication_event(user=user, action="authentication.mfa_accepted")
            request.session.set_expiry(None)
            return redirect("health-live")
        attempts = int(request.session.get(MFA_ATTEMPTS_KEY, 0)) + 1
        request.session[MFA_ATTEMPTS_KEY] = attempts
        if attempts >= MAX_MFA_ATTEMPTS:
            request.session.flush()
            return redirect("login")
        form.add_error("token", "The authentication code was not accepted.")
    return render(request, "registration/mfa_verify.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    user = request.user
    if isinstance(user, User) and user.is_authenticated:
        record_authentication_event(user=user, action="authentication.logout")
    auth_logout(request)
    return redirect("login")


@login_required
@require_http_methods(["GET", "POST"])
def setup_mfa(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User) or not has_privileged_role(user=user):
        return HttpResponseForbidden("MFA enrollment is restricted to privileged accounts")

    pending = TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-id").first()
    form = TokenForm(request.POST or None)
    if request.method == "POST" and request.POST.get("action") == "start":
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        pending = TOTPDevice.objects.create(user=user, name="primary", confirmed=False)
        form = TokenForm()
    elif request.method == "POST" and request.POST.get("action") == "confirm":
        if pending is None:
            form.add_error(None, "Start enrollment before confirming a code.")
        elif form.is_valid() and pending.verify_token(form.cleaned_data["token"]):
            pending.confirmed = True
            pending.save(update_fields=("confirmed",))
            generated = replace_recovery_codes(user=user)
            otp_login(request, pending)
            _record_session_version(request, user)
            record_authentication_event(user=user, action="authentication.mfa_enrolled")
            return render(
                request,
                "registration/mfa_recovery_codes.html",
                {"recovery_codes": generated.plaintext},
            )
        else:
            form.add_error("token", "The authentication code was not accepted.")

    return render(
        request,
        "registration/mfa_setup.html",
        {"form": form, "device": pending, "config_url": pending.config_url if pending else None},
    )
