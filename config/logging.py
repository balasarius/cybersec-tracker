# SPDX-License-Identifier: Apache-2.0
"""Minimal structured logging without a third-party runtime dependency."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Render diagnostic logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id is not None:
            payload["correlation_id"] = str(correlation_id)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
