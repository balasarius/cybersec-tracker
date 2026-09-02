# SPDX-License-Identifier: Apache-2.0
"""Cyber Security Tracker configuration package."""

from config.celery import app as celery_app

__all__ = ("celery_app",)
