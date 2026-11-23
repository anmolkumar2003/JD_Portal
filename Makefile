COMPOSE ?= docker compose
API_RUN := $(COMPOSE) run --rm --no-deps api
WEB_RUN := $(COMPOSE) run --rm --no-deps web

.DEFAULT_GOAL := help
.PHONY: help env up down logs migrate test test-api test-web test-e2e lint lint-api lint-web format seed

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example if it does not exist
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

up: env ## Build and start all services in the background
	$(COMPOSE) up --build -d

down: ## Stop all services (add v=1 to also delete volumes)
	$(COMPOSE) down $(if $(v),-v,)

logs: ## Follow logs (optionally s=<service>)
	$(COMPOSE) logs -f --tail=200 $(s)

migrate: ## Apply Alembic migrations (stack must be up)
	$(COMPOSE) exec api alembic upgrade head

test: test-api test-web ## Run all tests

test-api: ## Run API tests (pytest)
	$(API_RUN) pytest

test-web: ## Type-check the web app (no web test runner yet)
	$(WEB_RUN) npm run typecheck

test-e2e: ## Playwright e2e (stack must be up + seeded; uses Docker Playwright image)
	# Same-site host.docker.internal so the refresh cookie works across web↔API ports.
	NEXT_PUBLIC_API_URL=http://host.docker.internal:8001 $(COMPOSE) up -d --force-recreate web
	@sleep 8
	docker run --rm --add-host=host.docker.internal:host-gateway \
		-e PLAYWRIGHT_BASE_URL=http://host.docker.internal:3000 \
		-v "$(CURDIR)/apps/web:/work" -w /work \
		mcr.microsoft.com/playwright:v1.49.1-jammy \
		bash -c "npm ci && npx playwright test"
	NEXT_PUBLIC_API_URL=http://localhost:8001 $(COMPOSE) up -d --force-recreate web

lint: lint-api lint-web ## Run all linters

lint-api: ## Ruff + mypy
	$(API_RUN) sh -c "ruff check . && ruff format --check . && mypy"

lint-web: ## ESLint + Prettier
	$(WEB_RUN) sh -c "npm run lint && npm run format:check"

format: ## Auto-format API and web code
	$(API_RUN) sh -c "ruff check --fix . && ruff format ."
	$(WEB_RUN) npm run format

seed: ## Seed demo org, users, pipeline stages and jobs (stack must be up, run migrate first)
	$(COMPOSE) exec api python -m app.seed
