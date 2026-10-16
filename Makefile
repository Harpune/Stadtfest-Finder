# Stadtfest-Finder – developer commands. Run everything from the repo root.
# See CLAUDE.md "Commands" and 00-docs/40-operations/lokale-entwicklung.md.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load local configuration (optional) and export it to all recipes.
-include .env
export

COMPOSE_DEV := docker compose -f infra/compose.dev.yaml
# Production stack checked with the Komodo template instead of the real stack environment.
COMPOSE_PROD_CHECK := STADTFEST_ENV_FILE=komodo-environment.example docker compose --env-file infra/komodo-environment.example -f infra/compose.yaml
CADDY_IMAGE := caddy:2.11-alpine
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
dev: install deps-up migrate ## Start local stack + API (reload) + worker + MCP server; Ctrl+C stops them
	@trap 'kill 0' INT TERM EXIT; \
	( $(BACKEND) uv run uvicorn stadtfest.bootstrap.app:create_app --factory --reload --reload-dir src --port $(API_PORT) --no-access-log ) & \
	( $(BACKEND) uv run python -m stadtfest.bootstrap.worker ) & \
	( $(BACKEND) uv run python -m stadtfest.bootstrap.mcp ) & \
	wait

.PHONY: mcp
mcp: ## Start only the MCP server (http://localhost:$$MCP_PORT/mcp, R15)
	$(BACKEND) uv run python -m stadtfest.bootstrap.mcp

.PHONY: seed
seed: migrate ## Load synthetic seed data into the local DB (idempotent, never in prod)
	$(BACKEND) uv run python ../seed/load.py

.PHONY: ai-eval
ai-eval: ## Compare AI search prompts with the configured providers, e.g. ZIPS="73430 89073" PROMPTS=v1,v2 (costs requests, never in CI)
	$(BACKEND) uv run python -m stadtfest.bootstrap.ai_eval $(ZIPS) $(if $(PROMPTS),--prompts $(PROMPTS)) $(if $(OUT),--out $(abspath $(OUT))) $(if $(PAUSE),--pause $(PAUSE))

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
	$(MAKE) infra-check

.PHONY: infra-check
infra-check: ## Validate the production stack (compose.yaml + Caddyfile) against the Komodo template
	$(COMPOSE_PROD_CHECK) config --quiet
	@grep -E '^(ACME_EMAIL|LINK_HOST|API_HOST|MCP_HOST_NAME|IMAGES_HOST|S3_BUCKET)=' infra/komodo-environment.example > infra/.caddy-check.tmp
	docker run --rm --env-file infra/.caddy-check.tmp -v "$(CURDIR)/infra/caddy/Caddyfile:/etc/caddy/Caddyfile:ro" $(CADDY_IMAGE) \
		caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile; status=$$?; rm -f infra/.caddy-check.tmp; exit $$status

.PHONY: smoke
smoke: ## Smoke-test a running deployment, e.g. API_URL=https://api.example.eu MCP_URL=https://mcp.example.eu
	$(BACKEND) uv run python -m stadtfest.bootstrap.smoke --api-url $(or $(API_URL),http://localhost:$(API_PORT)) --mcp-url $(or $(MCP_URL),http://localhost:$${MCP_PORT:-8001})

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
