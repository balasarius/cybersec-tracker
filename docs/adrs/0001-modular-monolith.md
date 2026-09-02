# ADR 0001: Begin with a modular Django monolith

- Status: Accepted in design; implementation gate pending
- Date: 2026-09-02
- Review date: Stage 1 review

## Context

The product has many related workflows and strong transactional consistency, audit, permission, and contributor-usability requirements, but an expected initial scale below 10,000 active findings.

## Decision

Use one Django deployment with explicitly separated applications and domain services. Permit workers as separate processes from the same codebase. Extract services only after measured operational need and an approved ADR.

## Alternatives considered

Microservices add network contracts, distributed transactions, deployment overhead, and contributor friction without established scaling evidence. Flask requires assembling capabilities Django already provides. A frontend SPA adds distributed UI state before demonstrated need.

## Consequences

Transactions and local development are simpler. Application dependency boundaries require review and tests because the runtime does not enforce them automatically.

## Security impact

Fewer network trust boundaries and one permission model reduce initial risk. A defect can affect more modules, so scoped authorization cannot rely only on module separation.

## Compatibility impact

Public REST, connector, and destination contracts remain versioned so later extraction is possible without changing consumers.
