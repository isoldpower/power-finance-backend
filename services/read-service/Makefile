.DEFAULT_GOAL := help
COMPOSE := docker compose -f compose.yaml


.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: run
run: ## Run the Kafka consumer locally (no docker; needs Kafka + postgres-read reachable from host)
	uv run python manage.py run_write_message_consumer

.PHONY: test
test: ## Run Read Service tests (postgres-read on host port 5434)
	uv run python manage.py test --settings=read_service.settings.test

.PHONY: build-image
build-image: ## Build the Read Service Docker image (context = repo root)
	$(COMPOSE) build read-write-consumer

.PHONY: up
up: ## Start the Read Service stack (read-write-consumer + postgres-read + kafka)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Read Service stack (read-write-consumer + postgres-read + kafka)
	$(COMPOSE) down
