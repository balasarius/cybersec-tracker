# Initial threat model

## Scope and trust boundaries

The initial scope covers browser/API clients, Django, PostgreSQL, Redis/Celery, object storage, source connectors, Jira/ServiceNow adapters, notifications, and administrators. External provider content, CSV data, webhooks, attachments, URLs, and plugin packages cross trust boundaries and are untrusted. PostgreSQL is authoritative; external tickets are projections.

## Principal threats and baseline controls

| Threat | Consequence | Baseline controls | Later validation |
|---|---|---|---|
| Cross-scope access or IDOR | Vulnerability disclosure or unauthorised action | Deny-by-default scoped services and object permission tests | Stage 2 threat review |
| Malicious provider/CSV content | Injection, XSS, formula execution, parser exhaustion | Schema validation, output encoding, size limits, CSV neutralisation, bounded jobs | Stages 4–5 security tests |
| Forged/replayed webhooks | False progress or workflow manipulation | Signatures, timestamp/replay checks, idempotency, review-only inbound default | Stage 7 contract tests |
| Credential theft | Source or destination compromise | Secret references, least scopes, redaction, rotation and health alerts | Stages 5 and 7 reviews |
| Incorrect automated merge/routing/risk | Hidden exposure or wrong owner/deadline | Explainable versioned decisions, initial analyst approval, reversibility, audit | Stages 3 and 6 datasets/tests |
| Remote ticket closes security work | False completion | External Done only submits remediation; Security alone confirms closure | Stages 3 and 7 tests |
| Audit tampering | Loss of accountability/evidence | Append-only domain operations, integrity chain, restricted export | Stage 2 tests |
| Job retry duplicates/loss | Missing or duplicated findings/tasks | Stable keys, constraints, transactions, checkpoints, outbox, repair queue | Stages 4–7 tests |
| SSRF through connectors or URLs | Internal network access/data theft | Declared outbound hosts, URL validation, isolated third-party plugins | Stage 5 review |
| Dependency/container compromise | Build or runtime compromise | Lock file, audit, minimal non-root image, CI with read-only permissions | Stages 1 and 9 |
| Availability/resource exhaustion | Ingestion or UI outage | Limits, timeouts, queue isolation, backoff, health probes and monitoring | Stage 9 load/resilience tests |

## Assumptions and deferred analysis

Deployment administrators and reviewed first-party code are trusted but auditable. Detailed data-flow diagrams, abuse cases, MFA recovery, report inference, backup access, object-storage malware handling, and connector egress policy require review in their delivery stages. Open questions in the decision register may change threats and must trigger updates.
