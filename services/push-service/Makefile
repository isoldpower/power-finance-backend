.DEFAULT_GOAL := help

GO         := go
BUILD_DIR  := build/
BINARY     := push-service
ENTRYPOINT := ./cmd
COMPOSE    := docker compose -f compose.yaml

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build
build: ## Compile the push-service binary into the build/ directory
	mkdir -p $(BUILD_DIR)
	$(GO) build -o $(BUILD_DIR)$(BINARY) $(ENTRYPOINT)

.PHONY: run
run: build ## Build and run the push-service locally (needs Kafka reachable from host)
	./$(BUILD_DIR)$(BINARY) run-api

.PHONY: test
test: ## Run push-service Go tests
	$(GO) test ./...

.PHONY: tidy
tidy: ## Tidy up Go module dependencies
	$(GO) mod tidy

.PHONY: build-image
build-image: ## Build the Push Service Docker image (context = repo root)
	$(COMPOSE) build push-service

.PHONY: up
up: ## Start the Push Service stack (push-service + kafka)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the Push Service stack (push-service + kafka)
	$(COMPOSE) down
