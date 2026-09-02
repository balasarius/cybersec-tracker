# SPDX-License-Identifier: Apache-2.0
.PHONY: install format format-check lint typecheck check migrations test coverage audit build up down

install:
	uv sync --frozen

format:
	uv run ruff format .
	uv run ruff check --fix .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy apps config connectors destination_adapters sdk

migrations:
	uv run python manage.py makemigrations --check --dry-run

test:
	uv run pytest

coverage:
	uv run coverage run -m pytest
	uv run coverage report

audit:
	uv run pip-audit

check: format-check lint typecheck migrations coverage

build:
	docker compose build

up:
	docker compose up --build

down:
	docker compose down
