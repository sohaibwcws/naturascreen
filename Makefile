.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down logs build migrate revision shell-api test test-core fmt \
        ingest-compounds data-mhcflurry data-response curate-targets

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Build and start the full local stack.
	$(COMPOSE) up --build -d

down: ## Stop the stack.
	$(COMPOSE) down

logs: ## Tail all service logs.
	$(COMPOSE) logs -f

build: ## Build images without starting.
	$(COMPOSE) build

migrate: ## Apply database migrations.
	$(COMPOSE) run --rm api alembic upgrade head

revision: ## Autogenerate a migration. Usage: make revision m="message"
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$(m)"

shell-api: ## Open a shell in the API container.
	$(COMPOSE) run --rm api bash

test: ## Run the full backend test suite (in-container).
	$(COMPOSE) run --rm api pytest -q

test-core: ## Run dependency-light core tests locally via uv (sim/scoring/normalization/disclaimer).
	cd api && uv run --no-project --python 3.12 --with numpy --with pydantic --with pydantic-settings --with httpx --with pytest pytest -q tests/core

fmt: ## Format + lint the backend.
	cd api && uv run ruff format . && uv run ruff check --fix .

# --- Data / model provisioning (real tooling; never committed) ---

ingest-compounds: ## Ingest natural compounds from COCONUT. Usage: make ingest-compounds n=500
	$(COMPOSE) run --rm api python -m naturascreen.services.compounds.ingest --limit $(or $(n),500)

data-mhcflurry: ## Fetch MHCflurry models into the worker image volume.
	$(COMPOSE) run --rm worker mhcflurry-downloads fetch

data-response: ## Train the response model on the public GDSC1 subset.
	$(COMPOSE) run --rm worker python -m naturascreen.services.response.train

curate-targets: ## Load curated cancer targets (with docking boxes) from the registry.
	$(COMPOSE) run --rm api python -m naturascreen.services.docking.curate_targets
