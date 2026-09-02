# SPDX-License-Identifier: Apache-2.0
"""Root URL configuration."""

from django.contrib import admin
from django.urls import path

from config import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live", health.live, name="health-live"),
    path("health/ready", health.ready, name="health-ready"),
]
