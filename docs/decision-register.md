# Decision register

## Confirmed

Confirmed decisions are maintained in `DESIGN.md` section 2.3. Architecture decisions are recorded under `docs/adrs/`. The initial baseline is a Python 3.13/Django 5.2 modular monolith, PostgreSQL system of record, Redis/Celery jobs, local authentication, Docker deployment, Apache-2.0 licensing, Security-gated completion, and OWASP Risk Rating authority.

## Open decisions

| ID | Decision | Needed by | Owner | Blocking Stage 1? |
|---|---|---|---|---|
| O-01 | Forecast daily observations, users, attachments, and retention storage. | Stage 4 capacity design | Product/Engineering | No |
| O-02 | Confirm exact provider products, licences, APIs, and scopes. | Stage 5 | Security/Engineering | No |
| O-03 | Define retention exceptions, legal holds, and regional constraints. | Stage 8 | Risk/Legal | No |
| O-04 | Define Jira projects, fields, workflow, and identities. | Stage 7 | Pilot team | No |
| O-05 | Select ServiceNow table/workflow. | Stage 7 | Service Management | No |
| O-06 | Approve external inbound field authority. | Stage 7 | Security/Product | No; conservative mode applies |
| O-07 | Approve report recipients and attachment disclosure. | Stage 8 | Risk/Security | No; summary-plus-link applies |
| O-08 | Approve evidence-pack control mappings. | Stage 8 | GRC | No |
| O-09 | Define authoritative scanners, freshness, delay, and fallback evidence. | Stage 3–4 | Security | No for scaffold; blocks validation behaviour |
| O-10 | Select shared/named triage model and targets. | Stage 3 | Security | No for scaffold |
| O-11 | Define assignment rejection and reassignment authority. | Stage 3 | Security/Product | No for scaffold |
| O-12 | Define reminder, escalation, and commitment defaults. | Stage 3 | Security | No for scaffold |
| O-13 | Define evidence requirements and Critical second-review rules. | Stage 3 | Security/Risk | No for scaffold |
| O-14 | Define recurrence thresholds and deadline treatment. | Stage 3 | Security/Risk | No for scaffold |
| O-15 | Define exception clock, drafting, second approval, and expiry behaviour. | Stage 8 | Risk Executive | No |
| O-16 | Define analyst visibility across sensitive business units. | Stage 2 | Security/Risk | No for scaffold; blocks RBAC completion |

Unresolved choices use only the conservative defaults explicitly stated in the design. They must not be silently inferred during feature implementation.
