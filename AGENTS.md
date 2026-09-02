# Engineering Agent Instructions

These instructions apply to the entire repository. They translate [DESIGN.md](DESIGN.md) into implementation and review requirements for human and automated contributors.

## 1. Authority and priorities

1. Follow the user's current request.
2. Follow this file for repository-wide engineering rules.
3. Treat `DESIGN.md` as the product and architecture specification.
4. Record a design conflict or significant new decision in an Architecture Decision Record (ADR); do not silently diverge from the design.
5. Preserve existing user changes and keep unrelated work out of the change.

If requirements are ambiguous, choose the safest reversible interpretation that preserves finding provenance and audit history. Ask for a decision when the choice changes security posture, externally visible behaviour, data retention, compatibility, or project scope.

## 2. Current product decisions

Implement against these established constraints:

- This is an Apache-2.0 open-source project for one organisation initially.
- Expected scale is fewer than 10,000 active findings; test with at least 50,000.
- Use Python 3.13, Django 5.2 LTS, Django REST Framework, PostgreSQL, Celery, Redis, S3-compatible object storage, Docker, and server-rendered Django/HTMX unless an approved ADR changes them.
- PostgreSQL is the system of record. Do not introduce OpenSearch, a separate analytics warehouse, microservices, or Kubernetes as an application requirement without measured need and review.
- Use secure local accounts initially and keep domain identities independent so OIDC/SAML can be linked later.
- Tasks have an owning team and one accountable owner.
- Unmatched findings remain unassigned for security-analyst review.
- Product Code and Infrastructure are the two primary task types.
- Policy targets use calendar days and configurable policies.
- Risk exceptions require approval by the designated Risk Executive.
- A qualifying rescan may move imported work to security validation, but only an authorised security analyst can confirm completion. Source disagreement requires review; recurrence reopens the existing task.
- Security analysts manage triage, owner follow-up, commitments, escalation, evidence review and final closure. Delivery owners cannot mark security work finally completed.
- Cross-source merges require analyst approval initially. Never discard original source records.
- Manual issues stay separate unless an analyst explicitly merges them.
- Jira and ServiceNow are the first external destinations. Until a field-authority matrix is approved, inbound changes are review-only.
- External destinations receive a summary and authenticated link by default.
- Retention is configurable by record class and defaults to three years.
- Reporting includes operational and monthly, quarterly, and yearly executive reporting.
- Compliance mappings cover ISO 27001, SOC 2, NIST CSF 2.0, and NIST SP 800-53.
- OWASP Risk Rating Methodology is the source of truth for task risk/severity. Security analysts approve triage assessments unless a complete, approved, high-confidence automation rule applies.
- Policy clocks start at first qualifying observation/import; triage and acknowledgement do not reset them.
- Acknowledgement is explicit, never inferred from viewing or notification delivery.
- Default escalation is owner, team lead, business-unit owner, Security leadership, then Risk Executive.
- Partial remediation of grouped work uses an analyst-controlled linked split with preserved history.
- Approved exceptions remain visible as active accepted risk, never completed remediation.
- Internal Security notes are separate from collaborative comments and restricted from owners/external destinations.

## 3. Engineering principles

### 3.1 Preserve distinctions

Do not collapse these concepts:

- A source record is the original provider payload or row.
- A finding is a normalised provider observation.
- A canonical observation links equivalent findings across sources.
- An issue is a security concern, including manual concerns.
- A task is the unit of remediation work.
- An external work item is a projection of a task into Jira, ServiceNow, or another destination.

Task status must never overwrite finding/source status. A remote ticket closing must not directly validate remediation. Merging must link and disposition records, never delete their history.

### 3.2 Prefer explicit domain operations

Put business rules in domain services and explicit commands, not views, serializers, model `save()` overrides, signals, templates, or Celery task bodies. Examples include:

- `resolve_asset`
- `evaluate_ownership`
- `propose_consolidation`
- `approve_consolidation`
- `calculate_policy_deadlines`
- `calculate_owasp_risk`
- `approve_risk_assessment`
- `record_follow_up`
- `escalate_remediation`
- `submit_remediation`
- `confirm_security_completion`
- `request_exception`
- `record_scan_validation`
- `reopen_recurring_task`
- `project_external_work_item`

Views and workers validate transport concerns, call one or more domain operations, and translate results. Avoid invisible side effects in generic persistence hooks.

### 3.3 Make automation explainable

Every automated assignment, grouping, risk calculation, deadline, state transition, completion, reopening, and synchronisation decision must expose:

- input identifiers and relevant values;
- rule/policy/fingerprint version;
- decision and confidence;
- matched and conflicting fields;
- timestamp and actor/process identity;
- correlation ID;
- an audit event.

### 3.4 Make processing idempotent

Imports, commands, webhooks, scheduled reports, notifications, and external synchronisation must tolerate retries. Use database constraints, stable idempotency keys, checkpoints, and transactional outbox records. Do not rely on a read-then-write duplicate check without a database constraint.

### 3.5 Secure by default

- Deny access unless explicitly granted.
- Scope all business queries to the organisation and the user's permitted business units/teams.
- Treat scanner content, CSV cells, webhook bodies, Markdown/HTML, filenames, URLs, and attachments as untrusted.
- Never log secrets, authentication headers, full raw payloads, or sensitive evidence.
- Store credentials through a secrets abstraction, not ordinary model fields or environment dumps.
- Use summary-plus-link for external disclosure unless destination configuration explicitly allows a data class.
- Require a reason for privileged and bulk operations.

## 4. Target repository structure

Use a modular Django monolith. A preferred layout is:

```text
config/                 Django settings, URL and process configuration
apps/
  accounts/             Local identity, MFA, roles, teams and future identity links
  tenancy/              Organisation and business-unit scope
  assets/               Canonical assets, aliases and reconciliation
  integrations/         Source accounts, imports, raw records and connector runtime
  findings/             Findings, identifiers and canonical observations
  ownership/            Assignment rules and explanations
  policies/             Versioned policy clocks and deadline calculation
  tasks/                Remediation tasks, grouping, progress and validation
  exceptions/           Risk exception workflow and Risk Executive decisions
  destinations/         Jira/ServiceNow projection and synchronisation
  notifications/        Email and signed outbound events
  reporting/            Definitions, snapshots, exports and metric catalogue
  audit/                Append-only domain audit trail and evidence exports
connectors/              Built-in source connector implementations
destination_adapters/    Built-in work-management adapters
sdk/                     Public connector and destination contracts
tests/                   Cross-module, contract, integration and end-to-end tests
docs/                    ADRs, review records and operator/contributor documentation
```

Keep app dependencies acyclic where practical. Cross-app write operations belong in services with explicit transaction boundaries. Shared utilities must not become a miscellaneous domain layer.

## 5. Coding standards

- Add `SPDX-License-Identifier: Apache-2.0` to new source files where comments are supported.
- Use type hints on production Python code. Run strict-enough static checks to catch incompatible types at module boundaries.
- Prefer UUID primary keys, timezone-aware UTC timestamps, database constraints, and explicit enums.
- Use relational columns for fields involved in filtering, rules, constraints, and reporting. Restrict JSONB to versioned provider metadata and rule documents.
- Make schema and data migrations reversible where feasible. Separate long-running data migrations from deployment migrations.
- Use decimal/fixed-point types for risk values; do not use binary floats for stored scores.
- Preserve immutable OWASP factor scores, rationales, evidence, methodology/profile versions and approval origin. Provider severity must not masquerade as calculated risk.
- Normalise package versions with ecosystem-aware parsers; never compare versions lexicographically.
- Use structured logs and correlation IDs. Error messages must be actionable without exposing sensitive data.
- Document public functions, plugin contracts, domain invariants, and non-obvious security decisions.
- Keep generated files reproducible and identify their generator.
- Do not add a dependency when the standard library or existing dependency provides a clear, maintained solution.

## 6. Required delivery stages and review gates

Work proceeds through the following stages. A stage may be split across pull requests, but its exit criteria do not change. Create a review record under `docs/reviews/` using the stage name and date. A review record contains scope, decisions, evidence, test results, risks, deferred work, reviewer, and approval state.

An agent may prepare subsequent-stage plans while waiting, but must not claim a gate is approved. Human approval is required for security boundaries, destructive migrations, public contracts, and each phase exit. If a user explicitly authorises multiple stages in one request, keep separate review evidence for each.

### Stage 0 — Requirements baseline

Deliver:

- traceable functional and non-functional requirements derived from `DESIGN.md`;
- resolved/open decision register;
- initial threat model and data classification;
- acceptance criteria for the first-team pilot;
- initial ADRs for the modular monolith, database, job queue, authentication, and Apache-2.0 licence.

Review gate:

- Product, security, and engineering agree on terminology and pilot scope.
- Open decisions have an owner and do not block Stage 1.
- No proposed feature contradicts confirmed product decisions.

### Stage 1 — Open-source repository foundation

Deliver:

- Django project skeleton and modular app boundaries;
- reproducible Docker Compose developer environment;
- pinned dependencies, linting, formatting, type checking and test configuration;
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, governance and ADR templates;
- CI safe for untrusted forks, with no protected secrets exposed;
- health endpoints and structured logging baseline.

Review gate:

- A new contributor can clone, start, migrate and test the project using documented commands.
- Licence, notices and dependency licences pass automated checks.
- CI fails on formatting, type, migration, security, or test failure.

### Stage 2 — Identity, authorisation and audit foundation

Deliver:

- local accounts, password reset, secure sessions and MFA for privileged roles;
- organisation, business unit, teams, membership and scoped RBAC;
- stable domain user identity with future external-identity links;
- append-only audit events, correlation IDs, reason capture and integrity-chain verification;
- audit timeline and privileged-read/export auditing.

Review gate:

- Threat-model review completed.
- Object and scope permissions have positive and negative tests.
- No normal application path can update/delete audit events.
- Authentication, MFA recovery, role escalation and cross-scope access tests pass.

### Stage 3 — Assets, findings and manual workflow

Deliver:

- canonical assets and source aliases with ambiguity review;
- normalised findings, CVE/CWE identifiers and raw-record references;
- manual issues kept separate by default;
- Product Code and Infrastructure tasks, progress updates, evidence and workflow transitions;
- unassigned analyst queue and ownership-rule dry run/explanation;
- versioned calendar-day policies and audited pause periods.
- OWASP risk scenarios, factor-level analyst assessment, immutable versions and methodology-profile configuration.
- security oversight queues, follow-ups, remediation commitments, escalation and analyst-gated completion.

Review gate:

- Domain model and migrations reviewed for constraints and provenance.
- No finding evidence is lost through edits, disposition, merge or task completion.
- Policy examples and boundary dates are approved by security/product reviewers.
- OWASP arithmetic, bands, severity matrix, technical fallback and highest-scenario task severity are independently reviewed.
- Accessibility and core owner workflow are manually reviewed.

### Stage 4 — CSV vertical slice and pilot readiness

Deliver:

- upload, mapping, preview, validation, commit and error report;
- deterministic row identity and retry-safe imports;
- asset reconciliation, ownership evaluation and task creation;
- source-confirmed validation readiness, analyst completion and recurrence reopening simulation;
- operational report and complete correlated audit timeline;
- initial-team onboarding and operator runbooks.

Review gate:

- The same CSV can be retried without duplicate findings or tasks.
- Malicious and malformed CSV cases pass security tests.
- A pilot team completes the agreed end-to-end acceptance scenario.
- Restore and failed-import replay have been demonstrated.

### Stage 5 — Connector framework and source integrations

Deliver:

- versioned connector SDK, manifest, schemas, mock server and contract suite;
- scheduled/incremental imports, checkpoints, backoff, rate limits and dead-letter repair;
- Nessus/Tenable, Wiz and SecurityScorecard connectors as provider access permits;
- integration health, freshness, bounded raw payload retention and replay.

Review gate:

- Each connector passes the same contract suite with sanitised fixtures.
- Provider terms, API scopes, outbound hosts and credential handling are reviewed.
- Schema drift and partial provider outages fail safely without data loss.

### Stage 6 — Cross-source consolidation and scan validation

Deliver:

- canonical observations and versioned fingerprints;
- component aliases and ecosystem-aware version handling;
- exact/probable/conflicting candidate explanations;
- analyst merge/split/reject/lock workflow and negative-match decisions;
- duplicate-task survivor preview with immutable merged-task history;
- multi-source validation readiness, disagreement review, analyst completion and recurrence reopening.

Review gate:

- Initial automatic merge remains disabled.
- A reviewed labelled dataset measures false merges and missed merges.
- Conflicting source states cannot silently complete a task.
- Consolidation is reversible in business terms while audit history remains immutable.

### Stage 7 — Jira and ServiceNow destinations

Deliver:

- versioned destination-adapter SDK and contract tests;
- summary-plus-link projection, remote identity/status monitoring and sync health;
- transactional outbox, idempotency, webhook verification, polling reconciliation, conflict detection and loop prevention;
- repair queue and analyst choice when consolidated tasks have multiple tickets;
- conservative review-only inbound mode until a field-authority matrix is approved.

Review gate:

- Jira and ServiceNow both demonstrate that the adapter contract is provider-neutral.
- Remote closure and automated scans cannot directly mark a security task completed.
- Duplicate, reordered, forged and missing webhook cases pass.
- A disclosure review verifies the exact fields sent to each destination.

### Stage 8 — Exceptions, reporting and compliance evidence

Deliver:

- Risk Executive exception approval, delegation, expiry, renewal and revocation;
- detailed operational reports and immutable executive snapshots;
- monthly, quarterly and yearly total risk, overdue work, business-unit risk and recurrence reports;
- ISO 27001, SOC 2, NIST CSF 2.0 and NIST SP 800-53 mapping configuration;
- signed/hash-manifested audit evidence packs and optional SIEM export.

Review gate:

- Requesters cannot approve their own exceptions.
- Historical reports reproduce from the recorded as-of time and definitions.
- Executive totals reconcile to authorised detailed records.
- Compliance reports do not claim certification or assessor conclusions.

### Stage 9 — Production readiness and release

Deliver:

- load, resilience, restore, upgrade, rollback and three-year-retention tests;
- hardened non-root containers, health probes, resource limits and immutable releases;
- SBOM, provenance, signed tags/images/artifacts and published checksums;
- monitoring, alerting, backup/restore, incident response, security disclosure and upgrade runbooks;
- release candidate and pilot feedback resolution.

Review gate:

- At least 50,000 active findings meet agreed performance targets.
- Recovery objectives are demonstrated, not inferred.
- No unresolved Critical/High security defect remains without documented acceptance.
- Product, security, operations and the pilot-team representative approve release.

### Stage 10 — Post-release learning

Deliver:

- measured assignment and consolidation accuracy;
- adoption, overdue-work, remediation and integration-health measures;
- contributor setup and plugin-development feedback;
- prioritised backlog and ADRs for any scale-driven architectural change.

Review gate:

- Automatic merge is enabled only for individually approved rule/confidence classes that meet agreed error thresholds.
- New infrastructure is justified by measurements.

## 7. Testing requirements

Testing is part of implementation, not a later stage. Every behaviour change includes tests in the same change. A feature is incomplete if only its happy path is tested.

### 7.1 Test layers

- **Unit tests** cover pure domain logic, permissions, validation, state machines, policy clocks, fingerprints, mappings and error paths without network access.
- **Risk calculation tests** cover the complete OWASP factor model, decimal boundaries, impact-source selection, matrix result, versioning, analyst approval and automation confidence gates.
- **Model/database tests** cover constraints, transactions, concurrency, indexes, migrations and PostgreSQL-specific behaviour against PostgreSQL—not SQLite.
- **Contract tests** apply one reusable suite to every connector and destination adapter.
- **Integration tests** cover Celery, Redis, object storage, email/webhooks, outbox delivery and external mock services.
- **End-to-end tests** cover a small number of critical user journeys through the real HTTP/UI boundary, including Security triage, owner follow-up and analyst-gated closure.
- **Security tests** cover authorisation, tenant/scope isolation, injection, XSS, SSRF, CSRF, CSV formula injection, unsafe files, webhook forgery, secret redaction and rate limiting.
- **Performance tests** cover imports, reporting, consolidation, sync bursts and retention/audit history at target capacity.
- **Recovery tests** cover restore, checkpoint replay, dead-letter replay, interrupted migrations and rollback compatibility.

### 7.2 Comprehensive unit-test standard

Every domain service must test:

1. successful operation;
2. every documented rejection and validation error;
3. permission allowed and denied cases;
4. minimum, maximum, empty, null and boundary values;
5. each legal and illegal state transition;
6. retry/idempotency behaviour;
7. concurrent or stale-version behaviour where records are mutable;
8. audit event content and secret redaction;
9. timezone/day-boundary behaviour;
10. recurrence or reversal behaviour where applicable.

Critical test matrices include:

- ownership rule priority, no match, conflicting match, disabled/effective-dated rule and bulk preview;
- policy severity/type/context matching, calendar boundaries, pauses, recalculation and version history;
- policy-clock origin, explicit acknowledgement, escalation ordering/skip reasons, partial-remediation split lineage and accepted-risk reporting;
- OWASP factor validation, likelihood/impact means at 3 and 6 boundaries, business-impact precedence, technical fallback, all matrix cells, highest-scenario aggregation, staleness and automation rejection;
- task state transitions, children, dispositions, exception states, scan-driven validation readiness, analyst-only completion and automatic reopening;
- follow-up due/stale calculations, reminders, deduplication, commitments, escalation thresholds, restricted internal notes and audit events;
- asset exact/weak/ambiguous identity, merge/split and alias history;
- cross-source fingerprint aliases, versions, ports/instances, confidence classes, rejection and survivor choice;
- multi-source resolved/active/stale/missing combinations;
- import pagination, duplicate pages, checkpoint failure, partial batch failure and provider deletion semantics;
- report as-of snapshots, metric versions, access filtering, totals, schedules and retention;
- remote status/user/field mappings, origin-loop prevention, conflict resolution and remote deletion;
- exception requester/approver separation, delegation, expiry, renewal and pause linkage;
- audit hash chaining, segment verification, redaction, export manifest and tombstones.

### 7.3 Coverage and quality gates

- Measure statement and branch coverage on first-party Python code.
- Require at least 90% statement coverage and 85% branch coverage repository-wide once Stage 3 begins.
- Require 100% branch coverage for permission predicates, OWASP risk calculations/severity matrix, policy deadline calculations, task/exception state-transition tables, audit-chain verification, consolidation decision classification, webhook signature verification and secret-redaction helpers.
- Coverage exceptions require an inline explanation and review; generated code and declarative migrations may be excluded explicitly.
- Coverage percentage never substitutes for meaningful assertions. Tests must verify persisted state, emitted events, audit content and absence of forbidden side effects.
- Run mutation testing periodically on policy, permissions, task state, consolidation and exception modules. Surviving material mutations become test defects.
- Flaky tests are defects. Quarantine requires an owner, issue, reason and expiry; quarantined tests do not satisfy a gate.

### 7.4 Test design rules

- Use factories/builders with explicit security-sensitive fields; avoid giant shared fixtures.
- Freeze time through an injected clock for deadline, expiry, report and recurrence tests.
- Inject UUID generation and provider clients where determinism matters.
- Use synthetic CVEs/assets and sanitised provider fixtures. Never commit production vulnerability data or credentials.
- Mock at network/process boundaries, not the domain logic being tested.
- Assert the number and meaning of external calls for retry and idempotency tests.
- Test migrations both forward and backward when reversible, including upgrade from the previous supported release.
- Keep tests order-independent and safe for parallel execution.
- Give regression tests a name or comment that identifies the prevented failure.

### 7.5 Required checks for every change

Before declaring work complete, run the applicable repository commands for:

1. formatting check;
2. linting;
3. type checking;
4. migration consistency/check;
5. unit and database tests;
6. contract/integration tests affected by the change;
7. coverage threshold;
8. dependency, licence, secret and security scans;
9. documentation/link checks;
10. container build for deployment-affecting changes.

If commands have not yet been established, Stage 1 must define stable commands in `Makefile`, `justfile`, or documented scripts. Never claim checks passed if they were not run. Report skipped checks and why.

## 8. Database and migration rules

- Prefer database-enforced uniqueness and check constraints for critical invariants.
- All import uniqueness includes source account and stable external identifier.
- Index tenant/organisation scope first where applicable and validate indexes with representative query plans.
- Protect concurrent commands using transactions, conditional updates, locks or optimistic versions as appropriate.
- Use expand/migrate/contract for changes spanning rolling releases.
- Do not delete or repurpose a column containing provenance/audit data until retention and migration are reviewed.
- Bulk recalculation, consolidation and retention operations require previews, bounded batches, progress and resumability.

## 9. API and compatibility rules

- Version public REST endpoints under `/api/v1/` and publish OpenAPI.
- Use explicit command endpoints for state changes.
- Require idempotency keys for retryable external commands.
- Paginate collections with stable ordering.
- Return stable machine-readable error codes without leaking sensitive data.
- Version connector manifests, finding envelopes, destination contracts, webhook events, report definitions and audit export schemas.
- Deprecate public fields/contracts before removal and document supported version windows.

## 10. Connector and destination rules

- Keep provider authentication, pagination, rate limits, field mapping and rich-text quirks inside adapters.
- Yield canonical envelopes to core services; adapters must not directly create domain tasks.
- Store raw records with bounded retention and checksum while restricting access.
- Checkpoints advance only after the corresponding committed batch.
- Declare outbound hosts and requested secret/data permissions.
- Provide fixture-based tests and a mock mode that needs no commercial account.
- Never load untrusted third-party Python into the web process. Prefer isolated containers for non-project plugins.

## 11. Audit and reporting rules

- Business audit events are not diagnostic logs.
- Corrections append compensating events; they do not rewrite history.
- Store rule, policy, mapping and metric-definition versions with resulting decisions.
- Report snapshots store as-of time, source freshness, filters, access context and content hashes.
- Every executive aggregate must drill through to authorised detailed records.
- Clearly distinguish findings, canonical observations, tasks, exceptions and stale source coverage in reports.
- Compliance mappings provide evidence organisation; they never assert certification.

## 12. Documentation requirements

Update documentation in the same change when modifying:

- user-visible workflow or terminology;
- configuration or environment variables;
- public APIs, schemas, events or plugin contracts;
- permissions, threat boundaries or disclosed data;
- migrations, deployment, backup, restore or upgrade steps;
- metrics and report definitions.

Significant decisions receive ADRs containing context, decision, alternatives, consequences, security impact, compatibility impact and review date.

## 13. Definition of done

A change is done only when:

- acceptance criteria are met;
- implementation respects module and security boundaries;
- migrations and rollback/compatibility implications are reviewed;
- comprehensive unit tests and applicable higher-level tests pass;
- required coverage is maintained;
- audit, permissions, idempotency and error handling are tested;
- user/operator/API documentation is updated;
- no secrets or production data are present;
- the relevant stage review record is updated;
- remaining risks and deferred work are explicit;
- the agent reports exactly which checks ran and their results.

Do not weaken tests, permissions, audit behaviour, validation or quality gates merely to make a change pass.
