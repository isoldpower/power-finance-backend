# Write Service — local targets.
#
# Invoke either directly:
#   make -C services/write-service <target>
# or via the root Makefile's subcommand router:
#   make write <target>
# (the root router rewrites `make write <target>` to `make -C
# services/write-service <target>`).

.DEFAULT_GOAL := help

COMPOSE      := docker compose -f compose.yaml
UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: run
run: ## Start the Write Service locally with uvicorn (autoreload, no docker)
	uv run uvicorn write_service.asgi:application \
		--reload --host $(UVICORN_HOST) --port $(UVICORN_PORT)

.PHONY: test
test: ## Run Write Service tests (sqlite, hermetic)
	uv run python manage.py test --settings=write_service.settings.test

.PHONY: build-image
build-image: ## Build the Write Service Docker image (context = repo root)
	$(COMPOSE) build write-service

.PHONY: up
up: ## Start the Write Service stack (write-service + postgres + immudb)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Write Service stack (write-service + postgres + immudb)
	$(COMPOSE) down