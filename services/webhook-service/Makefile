.DEFAULT_GOAL := help

GO         := go
BUILD_DIR  := build/
BINARY     := webhook-service
ENTRYPOINT := ./cmd
COMPOSE    := docker compose -f compose.yaml

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build
build: ## Compile the webhook-service binary into the build/ directory
	mkdir -p $(BUILD_DIR)
	$(GO) build -o $(BUILD_DIR)$(BINARY) $(ENTRYPOINT)

.PHONY: run
run: build ## Build and run the webhook-service locally (needs Kafka + Postgres reachable from host)
	./$(BUILD_DIR)$(BINARY) run-api

.PHONY: migrate
migrate: build ## Apply Goose migrations locally (needs Postgres reachable from host)
	./$(BUILD_DIR)$(BINARY) migrate up

.PHONY: test
test: ## Run webhook-service Go tests
	$(GO) test ./...

.PHONY: tidy
tidy: ## Tidy up Go module dependencies
	$(GO) mod tidy

.PHONY: build-image
build-image: ## Build the Webhook Service Docker image (context = repo root)
	$(COMPOSE) build webhook-service

.PHONY: up
up: ## Start the Webhook Service stack (webhook-service + migrate + postgres + kafka)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Webhook Service stack (webhook-service + migrate + postgres + kafka)
	$(COMPOSE) down
