# SPDX-License-Identifier: Apache-2.0
"""Tests for the structured diagnostic logging baseline."""

import json
import logging

from config.logging import JsonFormatter


def test_json_formatter_emits_expected_fields() -> None:
    record = logging.LogRecord("tracker", logging.INFO, __file__, 1, "ready %s", ("now",), None)
    record.correlation_id = "correlation-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "tracker"
    assert payload["message"] == "ready now"
    assert payload["correlation_id"] == "correlation-1"
    assert payload["timestamp"].endswith("+00:00")


def test_json_formatter_omits_missing_correlation_id() -> None:
    record = logging.LogRecord("tracker", logging.WARNING, __file__, 1, "warning", (), None)

    payload = json.loads(JsonFormatter().format(record))

    assert "correlation_id" not in payload
