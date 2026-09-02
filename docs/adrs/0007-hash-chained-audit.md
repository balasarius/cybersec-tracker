# ADR 0007: Use append-only hash-chained audit events

- Status: Proposed for Stage 2 approval
- Date: 2026-09-03
- Review date: Stage 2 review

## Context

The platform must reconstruct security decisions and detect alteration without treating diagnostic logs as business evidence.

## Decision

Append immutable, per-organisation sequenced events through a transactional service. Serialize appends by locking an organisation audit head. Each event hashes canonical content and the previous hash. Application model/query operations and a PostgreSQL trigger reject updates and deletion. Corrections append compensating events.

## Alternatives considered

Ordinary mutable history tables cannot demonstrate integrity. A single global chain creates unnecessary contention. External immutable ledgers add an operational dependency before need is measured.

## Consequences

Integrity verification is deterministic and organisation-scoped. High-volume performance must be measured; later segmentation/checkpointing may be introduced without rewriting events.

## Security impact

Secret-like fields are recursively redacted before persistence. Database administrators remain a trusted operational boundary; signed exports and external SIEM anchoring are deferred to later evidence stages.

## Compatibility impact

Audit event and export schemas must be versioned before becoming public contracts. Existing event content is never rewritten during schema evolution.
