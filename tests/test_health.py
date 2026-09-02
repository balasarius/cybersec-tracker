# SPDX-License-Identifier: Apache-2.0
"""Tests for process and dependency health endpoints."""

from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.test import Client


def test_liveness_does_not_require_dependencies(client: Client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_reports_database_available(client: Client) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readiness_fails_closed_when_database_is_unavailable(client: Client) -> None:
    with patch("config.health.connection.cursor", side_effect=OperationalError("secret details")):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert b"secret details" not in response.content
