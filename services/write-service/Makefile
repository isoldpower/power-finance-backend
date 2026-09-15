.DEFAULT_GOAL := help

COMPOSE      := docker compose -f compose.yaml
UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000
REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../..)
SANDBOX_RUNNER := $(REPO_ROOT)/infrastructure/dev-host/run_sandbox_service.sh
SANDBOX_NAME ?= $(NAME)
SANDBOX_ENV_FILE = $(REPO_ROOT)/.sandbox/$(SANDBOX_NAME)-write-service.env
PORT ?= 8102
# Every long-running process the write-service image runs, minus the one-shot
# migrate job. Kept in step with services/write-service/compose.yaml — a sandbox
# missing one of these looks like a feature silently not working (automations that
# never fire, actions that never expire), not like a service that is down.
WRITE_PROCESSES = \
	"edge=uv run uvicorn write_service.asgi:application --port $(PORT) --reload" \
	"automation-engine=uv run python manage.py run_automation_engine" \
	"automation-scheduler=uv run python manage.py run_automation_scheduler" \
	"fraud-alerts=uv run python manage.py run_fraud_alerts_consumer" \
	"notifications=uv run python manage.py run_inbound_notifications_consumer" \
	"action-expiry=uv run python manage.py run_action_expiry_sweeper"
WRITE_REQUIRED = DATABASE_HOST DATABASE_PORT DATABASE_NAME DATABASE_USER \
	DATABASE_PASSWORD KAFKA_BOOTSTRAP_SERVERS REDIS_HOST REDIS_PORT \
	IMMUDB_HOST IMMUDB_PORT IMMUDB_USER IMMUDB_PASSWORD

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: run
run: ## Start the Write Service locally with uvicorn (autoreload, no docker)
	uv run uvicorn write_service.asgi:application \
		--reload --host $(UVICORN_HOST) --port $(UVICORN_PORT)

.PHONY: test
test: ## Run Write Service tests (pytest, sqlite, hermetic)
	uv run pytest -q

.PHONY: build-image
build-image: ## Build the Write Service Docker image (context = repo root)
	$(COMPOSE) build write-service

.PHONY: up
up: ## Start the Write Service stack (write-service + postgres + immudb)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Write Service stack (write-service + postgres + immudb)
	$(COMPOSE) down
guard-NAME:
	@if [ -z "$(SANDBOX_NAME)" ]; then \
		echo "Missing required variable: NAME (the sandbox to run as)"; \
		exit 1; \
	fi

.PHONY: sandbox
sandbox: guard-NAME ## Run the whole service for a sandbox — edge + all five consumers: NAME= [PORT=8102]
	@$(SANDBOX_RUNNER) "$(SANDBOX_ENV_FILE)" - "$(WRITE_REQUIRED)" $(WRITE_PROCESSES)
