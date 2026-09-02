# ADR 0005: License the project under Apache License 2.0

- Status: Accepted
- Date: 2026-09-02
- Review date: Before first stable release

## Context

The project is intended for broad open-source adoption and extension, including organisational and commercial use.

## Decision

License project contributions under Apache License 2.0, retain the repository `NOTICE`, and add SPDX identifiers to source files where supported.

## Alternatives considered

MIT is simpler but lacks an explicit patent grant. GPL/AGPL provides stronger copyleft but may reduce adoption and integration in intended environments.

## Consequences

Users receive permissive rights with patent protection and notice obligations. Contributors must only add compatible dependencies and content they can license.

## Security impact

No direct runtime impact. Public source enables scrutiny but does not replace secure development and disclosure practices.

## Compatibility impact

Dependency licence checks must reject incompatible terms, and distributed derivatives must preserve required notices.
