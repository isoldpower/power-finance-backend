# See README.md → "Make"
.DEFAULT_GOAL := help

unexport VIRTUAL_ENV

WRITE_SERVICE_DIR     := services/write-service
READ_SERVICE_DIR      := services/read-service
PUSH_SERVICE_DIR      := services/push-service
WEBHOOK_SERVICE_DIR   := services/webhook-service
ANTIFRAUD_SERVICE_DIR := services/antifraud-service
AI_SERVICE_DIR        := services/ai-service
CORRELATION_LIB_DIR := libraries/correlation-py
KAFKA_CLIENT_LIB_DIR := libraries/kafka-client-py
KAFKA_CONSUMER_LIB_DIR := libraries/kafka-consumer-py
SAGA_LIB_DIR         := libraries/saga-pattern-py
READ_AT_LEAST_LIB_DIR := libraries/read-at-least-py

UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000

REGISTRY      := ghcr.io
IMAGE_OWNER   := isoldpower
IMAGE_PREFIX  := $(REGISTRY)/$(IMAGE_OWNER)/power-finance
IMAGE_TAG     ?= $(shell git rev-parse --short HEAD)
DOCKER_SERVICES := write read push webhook antifraud ai
GATEWAY_IMAGE   := $(IMAGE_PREFIX)/api-gateway
GATEWAY_CONTEXT := infrastructure/kong
DOCKER_CONFIG_FILE := $(HOME)/.docker/config.json

PRECOMMIT_CONFIG := .pre-commit.yaml
HOOK_SENTINEL    := .git/hooks/pre-commit

ROUTER_TARGETS := write read push webhook antifraud ai
ROUTING        := $(filter $(firstword $(MAKECMDGOALS)),$(ROUTER_TARGETS))

$(HOOK_SENTINEL): $(PRECOMMIT_CONFIG)
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $@

.PHONY: write
write: | $(HOOK_SENTINEL) ## Route to write-service Makefile: `make write <subcommand>`
	@$(MAKE) -C $(WRITE_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: read
read: | $(HOOK_SENTINEL) ## Route to read-service Makefile: `make read <subcommand>`
	@$(MAKE) -C $(READ_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: push
push: | $(HOOK_SENTINEL) ## Route to push-service Makefile: `make push <subcommand>`
	@$(MAKE) -C $(PUSH_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: webhook
webhook: | $(HOOK_SENTINEL) ## Route to webhook-service Makefile: `make webhook <subcommand>`
	@$(MAKE) -C $(WEBHOOK_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: antifraud
antifraud: | $(HOOK_SENTINEL) ## Route to antifraud-service Makefile: `make antifraud <subcommand>`
	@$(MAKE) -C $(ANTIFRAUD_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: ai
ai: | $(HOOK_SENTINEL) ## Route to ai-service Makefile: `make ai <subcommand>`
	@$(MAKE) -C $(AI_SERVICE_DIR) $(ROUTED_ARGS)

ifneq ($(ROUTING),)
  ROUTED_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(ROUTED_ARGS):;@:)
endif

ifeq ($(ROUTING),)

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Sync the uv workspace + wire git pre-commit hook
	uv sync --all-packages --group dev
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $(HOOK_SENTINEL)

.PHONY: clean
clean: | $(HOOK_SENTINEL) ## Remove __pycache__ and bytecode artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

.PHONY: test
test: test-correlation test-libraries test-write test-read test-ai ## Run every test suite

.PHONY: test-correlation
test-correlation: | $(HOOK_SENTINEL) ## Run correlation-py library tests (unittest)
	uv run python -m unittest discover -s $(CORRELATION_LIB_DIR)/correlation/__tests__ -t $(CORRELATION_LIB_DIR)

.PHONY: test-libraries
test-libraries: | $(HOOK_SENTINEL) ## Run the pytest library suites (kafka-client, kafka-consumer, saga, read-at-least)
	cd $(KAFKA_CLIENT_LIB_DIR) && uv run pytest -q
	cd $(KAFKA_CONSUMER_LIB_DIR) && uv run pytest -q
	cd $(SAGA_LIB_DIR) && uv run pytest -q
	cd $(READ_AT_LEAST_LIB_DIR) && uv run pytest -q

.PHONY: test-write
test-write: | $(HOOK_SENTINEL) ## Run Write Service tests (pytest, postgres-write on host port 5433)
	cd $(WRITE_SERVICE_DIR) && uv run pytest -q

.PHONY: test-read
test-read: | $(HOOK_SENTINEL) ## Run Read Service tests (pytest, postgres-read on host port 5434)
	cd $(READ_SERVICE_DIR) && uv run pytest -q

.PHONY: test-ai
test-ai: | $(HOOK_SENTINEL) ## Run AI Service tests (pytest, postgres-ai on host port 5436)
	@$(MAKE) -C $(AI_SERVICE_DIR) test

.PHONY: lint
lint: | $(HOOK_SENTINEL) ## Check code with ruff
	uv run ruff check .

.PHONY: lint-fix
lint-fix: | $(HOOK_SENTINEL) ## Auto-fix ruff lint findings
	uv run ruff check --fix .

.PHONY: format
format: | $(HOOK_SENTINEL) ## Format code with ruff
	uv run ruff format .

.PHONY: format-check
format-check: | $(HOOK_SENTINEL) ## Verify formatting without writing changes
	uv run ruff format --check .

# Each Django service is its own package root, and both own a top-level
# `background_workers`. One mypy run over both would see two files claiming the
# same module name and refuse to check either, so they are checked separately.
.PHONY: typecheck
typecheck: | $(HOOK_SENTINEL) ## Run mypy against services + libraries
	uv run mypy services/write-service libraries
	uv run mypy services/read-service
	uv run mypy services/ai-service

.PHONY: precommit-install
precommit-install: ## Force-reinstall the git pre-commit hook
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $(HOOK_SENTINEL)

.PHONY: precommit
precommit: | $(HOOK_SENTINEL) ## Run all pre-commit hooks against the entire tree
	uv run pre-commit run --config $(PRECOMMIT_CONFIG) --all-files

.PHONY: docker-auth-check
docker-auth-check:
	@grep -q '"$(REGISTRY)"' $(DOCKER_CONFIG_FILE) 2>/dev/null || { \
		echo "Not authorized for $(REGISTRY) — no credentials found in $(DOCKER_CONFIG_FILE)."; \
		echo "Authorization is out of scope for this target. Run 'docker login $(REGISTRY)' first."; \
		exit 1; }

.PHONY: docker-build
docker-build: ## Build every service + the api-gateway image (override tag with IMAGE_TAG=...; default = git short SHA)
	@for svc in $(DOCKER_SERVICES); do \
		img=$(IMAGE_PREFIX)/$$svc-service; \
		echo "==> building $$img:latest, $$img:$(IMAGE_TAG)"; \
		docker build -f services/$$svc-service/Dockerfile \
			-t "$$img:latest" -t "$$img:$(IMAGE_TAG)" . || exit 1; \
	done
	@echo "==> building $(GATEWAY_IMAGE):latest, $(GATEWAY_IMAGE):$(IMAGE_TAG)"
	@docker build -t "$(GATEWAY_IMAGE):latest" -t "$(GATEWAY_IMAGE):$(IMAGE_TAG)" $(GATEWAY_CONTEXT)

.PHONY: docker-push
docker-push: docker-auth-check docker-build ## Build + push every service + the api-gateway to the GHCR registry
	@for svc in $(DOCKER_SERVICES); do \
		img=$(IMAGE_PREFIX)/$$svc-service; \
		echo "==> pushing $$img"; \
		docker push "$$img:latest" || exit 1; \
		docker push "$$img:$(IMAGE_TAG)" || exit 1; \
	done
	@echo "==> pushing $(GATEWAY_IMAGE)"
	@docker push "$(GATEWAY_IMAGE):latest"
	@docker push "$(GATEWAY_IMAGE):$(IMAGE_TAG)"

endif
