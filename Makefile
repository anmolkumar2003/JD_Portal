COMPOSE ?= docker compose
COMPOSE_PROD ?= docker compose -f docker-compose.prod.yml
API_RUN := $(COMPOSE) run --rm --no-deps api
WEB_RUN := $(COMPOSE) run --rm --no-deps web
E2E := docker compose -f docker-compose.e2e.yml
BACKUP_DIR ?= backups/manual
S3_BUCKET ?= cvs

.DEFAULT_GOAL := help
.PHONY: help env up down logs migrate test test-api test-web test-e2e test-e2e-screenshots \
	lint lint-api lint-web format init-admin seed-demo cleanup-demo reference-data backup \
	backup-nightly restore prod-up prod-down prod-logs prod-migrate

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

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

init-admin: ## Create or reset a portal account interactively (run once per admin)
	$(COMPOSE) exec api python -m app.cli.init_admin

reference-data: ## Add any missing stages, email templates and departments (idempotent)
	$(COMPOSE) exec api python -m app.cli.reference_data

seed-demo: ## Load fake demo data (refuses unless APP_ENV=development; never runs automatically)
	$(COMPOSE) exec api python -m app.seed_demo

cleanup-demo: ## Delete all candidates, jobs and demo users, and empty the CV bucket (asks first)
	$(COMPOSE) exec api python -m app.cli.cleanup_demo

backup: ## Dump the database and copy the CV bucket into $(BACKUP_DIR)/<timestamp>
	@set -e; stamp=$$(date +%Y%m%d-%H%M%S); dir="$(BACKUP_DIR)/$$stamp"; mkdir -p "$$dir/cvs"; \
	$(COMPOSE) exec -T postgres sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > "$$dir/db.dump"; \
	$(COMPOSE) run --rm --no-deps -v "$(CURDIR)/$$dir:/backup" minio-init \
		mirror --quiet local/$(S3_BUCKET) /backup/cvs >/dev/null || true; \
	mkdir -p "$$dir/cvs"; \
	echo "Backup written to $$dir"

backup-nightly: ## Production backup (pg_dump + MinIO) into backups/nightly/
	@chmod +x scripts/backup.sh && ./scripts/backup.sh

restore: ## Restore from backups/nightly/<stamp> — make restore STAMP=20261123-020000
	@chmod +x scripts/restore.sh && ./scripts/restore.sh $(STAMP)

prod-up: ## Start production stack (requires .env from .env.production.example)
	$(COMPOSE_PROD) up -d --build

prod-down: ## Stop production stack
	$(COMPOSE_PROD) down

prod-logs: ## Follow production logs (s=<service>)
	$(COMPOSE_PROD) logs -f --tail=200 $(s)

prod-migrate: ## Apply migrations on the production stack
	$(COMPOSE_PROD) exec api alembic upgrade head

test: test-api test-web ## Run all tests

test-api: ## Run API tests (pytest, separate <db>_test database)
	$(API_RUN) pytest

test-web: ## Type-check the web app
	$(WEB_RUN) npm run typecheck

# The e2e stack is a separate compose project with throwaway storage; it does not restart or
# reconfigure the development stack, and the demo password only exists for this run.
# Screenshots run as a separate target so their long viewport matrix cannot time out the suite.
test-e2e: ## Playwright e2e (excludes screenshot projects) in an isolated stack
	@set -e; \
	export E2E_PASSWORD="E2e!$$(openssl rand -hex 12)"; \
	trap '$(E2E) --profile runner down -v --remove-orphans >/dev/null 2>&1' EXIT; \
	$(E2E) up -d --build --wait postgres redis minio minio-init mailpit api worker web; \
	$(E2E) exec -T api alembic upgrade head; \
	$(E2E) exec -T -e DEMO_PASSWORD="$$E2E_PASSWORD" api python -m app.seed_demo >/dev/null; \
	$(E2E) --profile runner run --rm -e E2E_PASSWORD playwright \
		bash -c 'npm ci --legacy-peer-deps --no-audit --no-fund --loglevel=error && npx playwright test --project=chromium'

test-e2e-screenshots: ## Playwright screenshot projects only (longer timeout)
	@set -e; \
	export E2E_PASSWORD="E2e!$$(openssl rand -hex 12)"; \
	trap '$(E2E) --profile runner down -v --remove-orphans >/dev/null 2>&1' EXIT; \
	$(E2E) up -d --build --wait postgres redis minio minio-init mailpit api worker web; \
	$(E2E) exec -T api alembic upgrade head; \
	$(E2E) exec -T -e DEMO_PASSWORD="$$E2E_PASSWORD" api python -m app.seed_demo >/dev/null; \
	$(E2E) --profile runner run --rm -e E2E_PASSWORD \
		-v "$(CURDIR)/docs:/work/docs" playwright \
		bash -c 'npm ci --legacy-peer-deps --no-audit --no-fund --loglevel=error && npx playwright test --project=screenshots'

lint: lint-api lint-web ## Run all linters

lint-api: ## Ruff + mypy
	$(API_RUN) sh -c "ruff check . && ruff format --check . && mypy"

lint-web: ## ESLint + Prettier + tsc
	$(WEB_RUN) sh -c "npm run lint && npm run format:check && npm run typecheck"

format: ## Auto-format API and web code
	$(API_RUN) sh -c "ruff check --fix . && ruff format ."
	$(WEB_RUN) npm run format
