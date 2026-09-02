# ADR 0004: Start with local authentication and stable domain identities

- Status: Accepted in design; implementation gate pending
- Date: 2026-09-02
- Review date: Stage 2 review

## Context

The first deployment requires secure accounts without committing to one organisation's identity provider, while later OIDC/SAML linkage must not change task ownership or audit actors.

## Decision

Use Django-backed local accounts initially. Introduce stable internal user identities and separate external identity links. Stage 2 adds secure password reset, sessions, privileged-role MFA, and scoped RBAC.

## Alternatives considered

OIDC-only would impede local evaluation and choose an integration before discovery. Provider identifiers as user keys would couple domain history to a mutable external directory.

## Consequences

The project must securely operate credentials and MFA in Stage 2. Future federation links to rather than replaces domain identities.

## Security impact

Local authentication expands credential risk and requires Argon2id, throttling, secure recovery, session controls, MFA, and audit. The current Stage 1 scaffold is not production authentication.

## Compatibility impact

External identity fields are additive; audit and ownership references retain stable internal identifiers.
