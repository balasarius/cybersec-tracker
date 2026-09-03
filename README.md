# Cyber Security Tracker

An open-source, plugin-based platform for importing, assigning, grouping, and tracking security remediation work.

The initial architecture and product specification are in [DESIGN.md](DESIGN.md).

Repository-wide implementation, testing, and staged review requirements are in [AGENTS.md](AGENTS.md).

Licensed under the [Apache License 2.0](LICENSE).

## Development status

The project is in its repository-foundation stage and is not ready for production use. Product behaviour is specified in `DESIGN.md`; staged implementation and review gates are in `AGENTS.md`.

## Quick start

Install Git and Docker with Compose, then run:

```bash
cp .env.example .env
docker compose build
docker compose run --rm web python manage.py migrate
docker compose up
```

Open <http://localhost:8000/health/ready>. See [CONTRIBUTING.md](CONTRIBUTING.md) for local Python checks and contribution requirements.

If Docker itself reports permission denied while accessing its daemon socket, either use `sudo`
for all `docker compose` commands or configure Docker access for your user according to your
Docker installation. Membership of the conventional `docker` group grants root-equivalent host
access and should be treated accordingly. The application containers still run as the unprivileged
`tracker` user.
