# Initial data classification

| Class | Examples | Default classification | Default handling |
|---|---|---|---|
| Public | Source code, documentation, synthetic fixtures, release artifacts | Public | May be published after review. |
| Internal | Non-sensitive configuration, operational metrics, team names | Internal | Authenticated access; disclose externally only when configured. |
| Confidential security | Findings, assets, scan evidence, remediation detail, internal comments | Confidential | Scoped least-privilege access, encryption in transit/at rest, no external projection by default. |
| Restricted | Credentials, tokens, sensitive attachments, internal Security notes, vulnerability embargoes | Restricted | Secrets abstraction or protected object storage; never log; explicit audited access; never project by default. |
| Audit/governance | Audit events, exception decisions, risk approvals, report snapshots | Confidential and integrity-critical | Append-only controls, authorised export, retention and legal-hold rules. |

External tasks receive a non-sensitive summary and authenticated link by default. Raw source payloads and evidence use bounded retention, defaulting to three years where the design has not defined a more specific lifecycle. Production data must never enter source control, fixtures, screenshots, or public issue discussions.
