# Requirements baseline

This baseline traces the implementation to [DESIGN.md](../DESIGN.md). Detailed acceptance rules remain authoritative there.

| ID | Requirement | Design reference | Initial delivery stage |
|---|---|---|---|
| ING-01 | Import retry-safe findings from CSV, manual entry, SecurityScorecard, Wiz, and Nessus/Tenable through versioned connectors. | 5.1, 7 | 4–5 |
| AST-01 | Reconcile source identities to canonical assets and queue ambiguity for Security. | 5.2 | 3–4 |
| COR-01 | Preserve source findings while consolidating equivalent cross-source observations with analyst approval. | 5.4 | 6 |
| TSK-01 | Group compatible findings into Product Code or Infrastructure remediation tasks. | 5.3–5.5 | 3–6 |
| OWN-01 | Apply explainable ownership rules; leave unmatched work unassigned. | 5.2 | 3–4 |
| RSK-01 | Use analyst-approved OWASP Risk Rating assessments as the task risk and severity authority. | 5.7 | 3 |
| POL-01 | Apply versioned calendar-day policies from the first qualifying observation. | 5.8 | 3 |
| SEC-01 | Give Security control of triage, follow-up, escalation, validation, and final closure. | 5.5–5.6 | 3 |
| EXC-01 | Track Risk Executive-approved exceptions as active, expiring accepted risk. | 5.9 | 8 |
| DST-01 | Project summary-plus-link tasks to Jira and ServiceNow while keeping security state authoritative. | 5.12 | 7 |
| AUD-01 | Maintain a complete append-only audit history with provenance and correlation. | 13 | 2 onward |
| REP-01 | Produce authorised detailed and monthly, quarterly, and yearly executive reporting. | 5.11 | 8 |
| SEC-NF-01 | Deny access by default, scope data, validate untrusted content, and avoid secret disclosure. | 10 | all |
| REL-NF-01 | Use idempotent transactions, checkpoints, outbox delivery, retries, and repair queues. | 7, 11 | 4 onward |
| OPS-NF-01 | Provide containerised, observable, recoverable operation using open components. | 12–13, 20 | 1 onward |
| PERF-NF-01 | Support fewer than 10,000 expected active findings and validate at least 50,000 before release. | 11, 14 | 9 |

Requirements are refined into issue-level acceptance criteria before implementation. A change to a confirmed decision updates this table, the design, and an ADR where architectural or security consequences are material.
