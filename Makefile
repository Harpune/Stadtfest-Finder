# Stadtfest-Finder – developer commands. Run everything from the repo root.
# See CLAUDE.md "Commands" and 00-docs/40-operations/lokale-entwicklung.md.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load local configuration (optional) and export it to all recipes.
-include .env
export

COMPOSE_DEV := docker compose -f infra/compose.dev.yaml
BACKEND := cd backend &&
API_PORT ?= 8000

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.env:
	@cp .env.example .env
	@echo "Created .env from .env.example"

.PHONY: install
install: .env ## Install backend dependencies
	$(BACKEND) uv sync --frozen

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
seed: ## Load synthetic seed data into the local DB (available from R02)
	@echo "No seed data yet – added in R02 (00-docs/10-specs/R02-katalog-backend.md)."

.PHONY: gen
gen: ## Regenerate code from api/openapi.yaml (backend models + mobile client)
	$(BACKEND) uv run datamodel-codegen

.PHONY: fmt
fmt: ## Format all code
	$(BACKEND) uv run ruff format src tests migrations && uv run ruff check --fix src tests migrations

.PHONY: lint
lint: ## Lint + type check + architecture rules + OpenAPI lint
	$(BACKEND) uv run ruff format --check src tests migrations
	$(BACKEND) uv run ruff check src tests migrations
	$(BACKEND) uv run mypy src
	$(BACKEND) uv run lint-imports
	npx --yes @stoplight/spectral-cli@6 lint --fail-severity=warn api/openapi.yaml

.PHONY: test
test: ## Unit + integration + contract tests (integration/contract need Docker)
	$(BACKEND) uv run pytest

.PHONY: test-unit
test-unit: ## Unit tests only (no Docker needed)
	$(BACKEND) uv run pytest tests/unit

.PHONY: gen-check
gen-check: gen ## Fail if generated code is out of date
	@git diff --exit-code -- backend/src/stadtfest/generated || \
		(echo "Generated code is out of date – run 'make gen' and commit the result." && exit 1)

.PHONY: check
check: lint gen-check test ## Everything CI runs – must pass before finishing a task
