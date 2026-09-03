# Contributing

Thank you for helping build Cyber Security Tracker. By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development setup

Requirements are Git, Docker with Compose, and optionally Python 3.13 with `uv` for host-based checks.

```bash
cp .env.example .env
docker compose build
docker compose run --rm web python manage.py migrate
docker compose up
```

The web application is available at <http://localhost:8000>; liveness and readiness are exposed at `/health/live` and `/health/ready`.

For local checks:

```bash
uv sync --frozen
make check
make audit
```

## Change requirements

- Open an issue for material product, security, compatibility, or architecture changes.
- Add an ADR under `docs/adrs/` for significant decisions.
- Add tests with every behaviour change and follow the gates in [AGENTS.md](AGENTS.md).
- Use synthetic security data only. Never include customer assets, findings, payloads, or credentials.
- Add `SPDX-License-Identifier: Apache-2.0` to source files where comments are supported.
- Use focused commits and explain security impact and verification in the pull request.

Contributions are made under the repository's [Apache License 2.0](LICENSE).
