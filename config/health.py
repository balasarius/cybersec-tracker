# SPDX-License-Identifier: Apache-2.0
"""Process and dependency health endpoints."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(_request: object) -> JsonResponse:
    """Report that the web process can serve requests."""
    return JsonResponse({"status": "ok"})


@require_GET
def ready(_request: object) -> JsonResponse:
    """Report readiness after verifying the system-of-record database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
