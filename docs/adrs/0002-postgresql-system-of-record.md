# ADR 0002: Use PostgreSQL as the system of record

- Status: Accepted in design; implementation gate pending
- Date: 2026-09-02
- Review date: Stage 1 review

## Context

The platform needs relational integrity, concurrency control, reporting, provenance, immutable history, and retry-safe uniqueness.

## Decision

Use supported PostgreSQL releases for all environments and tests. Store searchable domain fields relationally and reserve JSONB for versioned provider metadata and rule documents.

## Alternatives considered

SQLite cannot validate required PostgreSQL behaviour. A document database weakens relational constraints. A search engine or warehouse creates another authority and is not justified at initial scale.

## Consequences

Development requires PostgreSQL, usually through Compose. Schema design and migration discipline are central.

## Security impact

Database constraints support provenance and isolation invariants. Deployment must provide encryption, restricted credentials, backup protection, and audit controls.

## Compatibility impact

PostgreSQL-specific migrations and query behaviour are supported; alternative database engines are not an initial compatibility goal.
