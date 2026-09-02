# SPDX-License-Identifier: Apache-2.0
"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as account_views
from config import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", account_views.login_view, name="login"),
    path("accounts/mfa/setup/", account_views.setup_mfa, name="mfa-setup"),
    path("accounts/mfa/verify/", account_views.verify_mfa, name="mfa-verify"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("health/live", health.live, name="health-live"),
    path("health/ready", health.ready, name="health-ready"),
]
