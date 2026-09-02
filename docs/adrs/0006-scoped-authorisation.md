# ADR 0006: Scope authorization by organisation and business unit

- Status: Proposed for Stage 2 approval
- Date: 2026-09-03
- Review date: Stage 2 review

## Context

Security needs broad operational visibility, while ordinary analysts and delivery teams should not automatically see unrelated or particularly sensitive assets.

## Decision

Use stable organisation memberships with explicit roles. Security administrators, senior Security analysts, and Risk Executives may receive organisation-wide access to non-sensitive units. Ordinary Security analysts and auditors use explicit business-unit grants. A sensitive unit always requires an explicit grant. Delivery owners receive team/task scope. Domain services make explicit access decisions and deny by default.

## Alternatives considered

Universal Security access is operationally simple but overexposes sensitive areas. Fully explicit grants for every senior analyst add administration and increase the chance that urgent organisation-wide work is invisible. Django groups alone lack the required organisation and object scope.

## Consequences

Access decisions return an explanation and can be tested independently. Grant lifecycle and nested-unit semantics require explicit administration; initial grants do not implicitly inherit to descendants.

## Security impact

Cross-organisation access is always denied. Sensitive-unit grants override broad roles. Privileged roles additionally require an MFA-verified session. All privileged reads and grant changes must emit audit events as their endpoints are introduced.

## Compatibility impact

Future OIDC/SAML groups map to internal memberships and grants rather than becoming authorization authorities directly.
