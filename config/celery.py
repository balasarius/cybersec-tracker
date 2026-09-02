# SPDX-License-Identifier: Apache-2.0
"""Celery application configuration."""

import os

# Celery does not publish typing metadata.
from celery import Celery  # type: ignore[import-untyped]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("cybersec_tracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
