.DEFAULT_GOAL := help

GRADLE  := ./gradlew
COMPOSE := docker compose -f compose.yaml

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build
build: ## Build the shadow (fat) jar
	$(GRADLE) clean shadowJar

.PHONY: run
run: ## Run the Flink job locally (needs Kafka reachable from host)
	$(GRADLE) run

.PHONY: test
test: ## Run the test suite
	$(GRADLE) test

.PHONY: build-image
build-image: ## Build the Antifraud Service Docker image (context = repo root)
	$(COMPOSE) build antifraud-service

.PHONY: up
up: ## Start the Antifraud Service stack (antifraud-service + kafka)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Antifraud Service stack (antifraud-service + kafka)
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail the antifraud-service logs
	$(COMPOSE) logs -f antifraud-service
