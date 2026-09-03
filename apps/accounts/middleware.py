# SPDX-License-Identifier: Apache-2.0
"""Session invalidation and privileged MFA enforcement."""

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from apps.accounts.access import has_privileged_role
from apps.accounts.models import User
from apps.accounts.views import AUTHORIZATION_VERSION_KEY

EXEMPT_PREFIXES = (
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/mfa/setup/",
    "/accounts/mfa/verify/",
    "/accounts/password_reset/",
    "/accounts/reset/",
    "/health/",
)


class AuthorizationSessionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user
        if isinstance(user, User) and user.is_authenticated:
            session_version = request.session.get(AUTHORIZATION_VERSION_KEY)
            if session_version != user.authorization_version:
                logout(request)
                return redirect("login")
            is_verified = getattr(user, "is_verified", None)
            verified = bool(callable(is_verified) and is_verified())
            if (
                has_privileged_role(user=user)
                and not verified
                and not request.path.startswith(EXEMPT_PREFIXES)
            ):
                return redirect("mfa-setup")
        return self.get_response(request)
