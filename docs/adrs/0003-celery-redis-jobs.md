# ADR 0003: Use Celery with Redis for asynchronous jobs

- Status: Accepted in design; implementation gate pending
- Date: 2026-09-02
- Review date: Stage 1 review

## Context

Imports, reconciliation, notifications, reports, and destination synchronisation require scheduled, retryable background execution.

## Decision

Use Celery workers and beat with Redis as broker/result backend. PostgreSQL transactions, checkpoints, idempotency keys, and an outbox—not broker delivery—determine business correctness.

## Alternatives considered

Synchronous requests cannot handle provider latency and bulk work safely. A custom queue increases maintenance. Kafka is unjustified at projected scale and does not remove domain idempotency requirements.

## Consequences

Redis and worker processes become operational dependencies. Jobs require explicit timeouts, retry policies, observability, and repair handling.

## Security impact

Redis must not be publicly reachable. Task payloads must exclude secrets and unnecessarily sensitive raw data. Third-party plugins should be isolated from web and general workers.

## Compatibility impact

Domain commands remain independent of Celery task bodies so the execution mechanism can change later.
