# SPDX-License-Identifier: Apache-2.0
"""Correlation-ID validation and propagation middleware."""

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.audit.context import reset_correlation_id, set_correlation_id


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supplied = request.headers.get("X-Correlation-ID")
        try:
            value = uuid.UUID(supplied) if supplied else uuid.uuid4()
        except (ValueError, AttributeError):
            value = uuid.uuid4()
        request.correlation_id = value  # type: ignore[attr-defined]
        token = set_correlation_id(value)
        try:
            response = self.get_response(request)
        finally:
            reset_correlation_id(token)
        response["X-Correlation-ID"] = str(value)
        return response
