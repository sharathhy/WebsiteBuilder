COMPOSE = docker compose -f infra/docker-compose.yml
RUN = uv run

.PHONY: help up down logs seed install dev-api dev-worker dev-dashboard migrate migration test lint format typecheck check

help:          ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-15s %s\n", $$1, $$2}'

up:            ## Start the full stack in Docker (postgres, redis, api, worker, dashboard)
	$(COMPOSE) up --build -d
	@echo "Dashboard: http://localhost:5173  API docs: http://localhost:8000/api/docs"

down:          ## Stop the stack
	$(COMPOSE) down

logs:          ## Tail stack logs
	$(COMPOSE) logs -f --tail=100

seed:          ## Create dev users + demo campaign (mocked APIs, no keys needed)
	@if $(COMPOSE) ps --status running api >/dev/null 2>&1 && [ -n "$$($(COMPOSE) ps -q api)" ]; then \
		$(COMPOSE) exec api python -m leadforge.cli seed; \
	else cd api && $(RUN) python -m leadforge.cli seed; fi

install:       ## Install Python and dashboard dependencies locally
	uv sync
	cd dashboard && npm ci

migrate:       ## Apply migrations to DATABASE_URL
	cd api && $(RUN) alembic upgrade head

migration:     ## Autogenerate a migration: make migration m="add foo"
	cd api && $(RUN) alembic revision --autogenerate -m "$(m)"

dev-api:       ## Run the API with reload (needs local postgres + redis)
	cd api && $(RUN) uvicorn leadforge.main:app --reload --port 8000

dev-worker:    ## Run all queue workers locally
	$(RUN) python -m leadforge_worker.main

dev-dashboard: ## Run the dashboard dev server
	cd dashboard && npm run dev

test:          ## Python + dashboard tests
	$(RUN) pytest -q
	cd dashboard && npm test

lint:          ## ruff + eslint + prettier check
	$(RUN) ruff check .
	$(RUN) ruff format --check .
	cd dashboard && npm run lint && npm run format:check

format:        ## Auto-format everything
	$(RUN) ruff check --fix .
	$(RUN) ruff format .
	cd dashboard && npm run format

typecheck:     ## mypy + tsc
	$(RUN) mypy api/leadforge worker/leadforge_worker
	cd dashboard && npm run typecheck

check: lint typecheck test ## Everything CI runs
