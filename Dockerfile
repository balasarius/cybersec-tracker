# syntax=docker/dockerfile:1.7
# SPDX-License-Identifier: Apache-2.0
FROM python:3.13.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 10001 tracker \
    && useradd --system --uid 10001 --gid tracker --create-home tracker \
    && install -d -o tracker -g tracker -m 0750 /var/lib/celery

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=tracker:tracker . .
RUN uv sync --frozen --no-dev --no-editable

USER tracker
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
