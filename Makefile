# Stadtfest-Finder – developer commands. Run everything from the repo root.
# See CLAUDE.md "Commands" and 00-docs/40-operations/lokale-entwicklung.md.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load local configuration (optional) and export it to all recipes.
-include .env
export

COMPOSE_DEV := docker compose -f infra/compose.dev.yaml
BACKEND := cd backend &&
MOBILE := cd mobile &&
API_PORT ?= 8000

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.env:
	@cp .env.example .env
	@echo "Created .env from .env.example"

.PHONY: install
install: .env ## Install backend and mobile dependencies
	$(BACKEND) uv sync --frozen
	$(MOBILE) pnpm install --frozen-lockfile

.PHONY: deps-up
deps-up: .env ## Start local dependencies (Postgres/PostGIS, Redis, SeaweedFS, Keycloak)
	$(COMPOSE_DEV) up -d --wait

.PHONY: deps-down
deps-down: ## Stop local dependencies (data volumes are kept)
	$(COMPOSE_DEV) down

.PHONY: migrate
migrate: ## Apply database migrations
	$(BACKEND) uv run alembic upgrade head

.PHONY: dev
dev: install deps-up migrate ## Start local stack + API (reload) + worker; Ctrl+C stops API and worker
	@trap 'kill 0' INT TERM EXIT; \
	( $(BACKEND) uv run uvicorn stadtfest.bootstrap.app:create_app --factory --reload --reload-dir src --port $(API_PORT) --no-access-log ) & \
	( $(BACKEND) uv run python -m stadtfest.bootstrap.worker ) & \
	wait

.PHONY: seed
seed: migrate ## Load synthetic seed data into the local DB (idempotent, never in prod)
	$(BACKEND) uv run python ../seed/load.py

.PHONY: gen
gen: ## Regenerate code from api/openapi.yaml (backend models + mobile client) and design tokens
	$(BACKEND) uv run datamodel-codegen
	$(MOBILE) pnpm gen

.PHONY: fmt
fmt: ## Format all code
	$(BACKEND) uv run ruff format src tests migrations ../seed && uv run ruff check --fix src tests migrations ../seed
	$(MOBILE) pnpm fix

.PHONY: lint
lint: ## Lint + type check + architecture rules + OpenAPI lint
	$(BACKEND) uv run ruff format --check src tests migrations ../seed
	$(BACKEND) uv run ruff check src tests migrations ../seed
	$(BACKEND) uv run mypy src
	$(BACKEND) uv run lint-imports
	npx --yes @stoplight/spectral-cli@6 lint --fail-severity=warn api/openapi.yaml
	$(MOBILE) pnpm lint
	$(MOBILE) pnpm typecheck

.PHONY: test
test: ## Unit + integration + contract tests (integration/contract need Docker) + mobile Jest
	$(BACKEND) uv run pytest
	$(MOBILE) pnpm test --ci

.PHONY: test-unit
test-unit: ## Unit tests only (no Docker needed)
	$(BACKEND) uv run pytest tests/unit
	$(MOBILE) pnpm test --ci

.PHONY: test-e2e
test-e2e: ## Maestro flows against a running simulator/emulator with the dev build installed
	$(MOBILE) pnpm test:e2e

.PHONY: gen-check
gen-check: gen ## Fail if generated code is out of date
	@git diff --exit-code -- backend/src/stadtfest/generated mobile/src/api/generated mobile/src/theme/generated || \
		(echo "Generated code is out of date – run 'make gen' and commit the result." && exit 1)

.PHONY: check
check: lint gen-check test ## Everything CI runs – must pass before finishing a task
