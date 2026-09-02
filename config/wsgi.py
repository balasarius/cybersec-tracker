# SPDX-License-Identifier: Apache-2.0
"""WSGI application entry point."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
