# SPDX-License-Identifier: Apache-2.0
"""Request-local correlation context used by domain audit services."""

from contextvars import ContextVar, Token
from uuid import UUID

correlation_id: ContextVar[UUID | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(value: UUID) -> Token[UUID | None]:
    return correlation_id.set(value)


def reset_correlation_id(token: Token[UUID | None]) -> None:
    correlation_id.reset(token)
