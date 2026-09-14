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
OBSERVABILITY_LIB_DIR := libraries/observability-py
KAFKA_CLIENT_LIB_DIR := libraries/kafka-client-py
KAFKA_CONSUMER_LIB_DIR := libraries/kafka-consumer-py
SAGA_LIB_DIR         := libraries/saga-pattern-py
READ_AT_LEAST_LIB_DIR := libraries/read-at-least-py
FILTER_GRAMMAR_LIB_DIR := libraries/filter-grammar-py
WEBHOOK_CATALOG_LIB_DIR := libraries/webhook-catalog-py
CONTRACT_TESTS_DIR := infrastructure/tests/contract

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
test: test-correlation test-libraries test-write test-read test-ai test-go test-java test-contract ## Run every test suite

.PHONY: test-correlation
test-correlation: | $(HOOK_SENTINEL) ## Run correlation-py library tests (unittest)
	uv run python -m unittest discover -s $(CORRELATION_LIB_DIR)/correlation/__tests__ -t $(CORRELATION_LIB_DIR)

.PHONY: test-libraries
test-libraries: | $(HOOK_SENTINEL) ## Run the pytest library suites (observability, kafka-client, kafka-consumer, saga, read-at-least, filter-grammar, webhook-catalog)
	cd $(OBSERVABILITY_LIB_DIR) && uv run pytest -q
	cd $(KAFKA_CLIENT_LIB_DIR) && uv run pytest -q
	cd $(KAFKA_CONSUMER_LIB_DIR) && uv run pytest -q
	cd $(SAGA_LIB_DIR) && uv run pytest -q
	cd $(READ_AT_LEAST_LIB_DIR) && uv run pytest -q
	cd $(FILTER_GRAMMAR_LIB_DIR) && uv run pytest -q
	cd $(WEBHOOK_CATALOG_LIB_DIR) && uv run pytest -q

.PHONY: test-write
test-write: | $(HOOK_SENTINEL) ## Run Write Service tests (pytest, postgres-write on host port 5433)
	cd $(WRITE_SERVICE_DIR) && uv run pytest -q

.PHONY: test-read
test-read: | $(HOOK_SENTINEL) ## Run Read Service tests (pytest, postgres-read on host port 5434)
	cd $(READ_SERVICE_DIR) && uv run pytest -q

.PHONY: test-ai
test-ai: | $(HOOK_SENTINEL) ## Run AI Service tests (pytest, postgres-ai on host port 5436)
	@$(MAKE) -C $(AI_SERVICE_DIR) test

.PHONY: test-go
test-go: | $(HOOK_SENTINEL) ## Run the Go module tests (kafka-client-go, push-service, webhook-service)
	go test ./libraries/kafka-client-go/... ./libraries/observability-go/... ./services/push-service/... ./services/webhook-service/...

.PHONY: test-java
test-java: | $(HOOK_SENTINEL) ## Run the antifraud-service JVM tests
	@$(MAKE) -C $(ANTIFRAUD_SERVICE_DIR) test

.PHONY: test-contract
test-contract: | $(HOOK_SENTINEL) ## Run the cross-service contract suite (no infrastructure needed)
	uv run pytest $(CONTRACT_TESTS_DIR) -q

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
	uv run mypy $(CONTRACT_TESTS_DIR)

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

# See README.md → "Environment"
COMPOSE_ENV_LAYERS := $(wildcard .env) $(wildcard services/*/.env.compose)
COMPOSE_ENV_FLAGS  := $(foreach layer,$(COMPOSE_ENV_LAYERS),--env-file $(layer))
COMPOSE            := docker compose $(COMPOSE_ENV_FLAGS)

.PHONY: env-layers
env-layers: ## Show which env files the compose targets will stack, in order
	@echo "$(COMPOSE_ENV_LAYERS)" | tr ' ' '\n' | cat -n

.PHONY: env-resolve
env-resolve: ## Print the fully resolved compose config after layering
	@$(COMPOSE) config

.PHONY: up
up: ## Start the whole stack with the layered environment
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the whole stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow logs for the whole stack
	$(COMPOSE) logs -f

# See README.md → "Shared dev environment"
BASELINE_PROJECT         := pf-baseline
BASELINE_NETWORK_NAME    := $(BASELINE_PROJECT)_default
SANDBOX_PROJECT_PREFIX   := pf-sbx-
SANDBOX_ROUTE_KEY_PREFIX := sandbox:route:
SANDBOX_ROUTE_TTL_SECONDS ?= 604800
SANDBOX_HTTP_PORT_write-service   := 8000
SANDBOX_HTTP_PORT_read-service    := 8000
SANDBOX_HTTP_PORT_ai-service      := 8000
SANDBOX_HTTP_PORT_push-service    := 8001
SANDBOX_HTTP_PORT_webhook-service := 8002
SANDBOX_HTTP_PORT         = $(or $(SANDBOX_HTTP_PORT_$(SERVICE)),8000)
SANDBOX_HTTP_SERVICES    := write-service read-service ai-service push-service webhook-service
SANDBOX_ENV_DIR          := .sandbox
DEV_HOST                 ?= localhost
LOCAL_SERVICE_PORT       ?= 8100
# The dev host account is rarely your laptop account; ssh defaults to the latter.
DEV_HOST_USER            ?=

BASELINE_COMPOSE  := $(COMPOSE) -p $(BASELINE_PROJECT) -f compose.yaml -f compose.baseline.yaml --profile local-elastic
SANDBOX_DATASTORE_FILES = $(if $(ISOLATED),-f compose.sandbox-datastores.yaml,)
# Live source mount is the default; BAKED=1 runs the image as built instead.
SANDBOX_LIVE_FILES      = $(if $(BAKED),,-f compose.sandbox-live.yaml)
SANDBOX_COMPOSE    = $(COMPOSE) -p $(SANDBOX_PROJECT_PREFIX)$(NAME) -f compose.sandbox.yaml $(SANDBOX_LIVE_FILES) $(SANDBOX_DATASTORE_FILES)
SANDBOX_SERVICE    = sbx-$(SERVICE)
SANDBOX_CONTAINER  = $(SANDBOX_PROJECT_PREFIX)$(NAME)-$(SANDBOX_SERVICE)-1
SANDBOX_ADDRESS_FORMAT := {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}
REDIS_IN_BASELINE  = $(BASELINE_COMPOSE) exec -T gateway-redis redis-cli
SANDBOX_ROUTE_KEY  = $(SANDBOX_ROUTE_KEY_PREFIX)$(NAME):$(SERVICE)

guard-%:
	@if [ -z "$($*)" ]; then \
		echo "Missing required variable: $*"; \
		exit 1; \
	fi

# The power-finance/*:dev tags live in no registry, so `up` would attempt a pull and
# log "pull access denied" for each. They also have to be built one service per
# tag: write-service and its six consumers share a tag, as do read-service and its
# jobs, and BuildKit exports them in parallel — several services naming the same
# tag fail with `image "...": already exists`. Building only the canonical service
# behind each tag resolves every image exactly once.
BASELINE_BUILD_SERVICES := write-service read-service ai-service push-service \
	webhook-service antifraud-jobmanager api-gateway

.PHONY: baseline-build
baseline-build: ## Build every baseline image, one per tag (safe to re-run; cached)
	$(BASELINE_COMPOSE) build $(BASELINE_BUILD_SERVICES)

.PHONY: baseline-up
baseline-up: baseline-build ## Start the shared baseline stack on the dev host (tuned, Kibana off, Jaeger on)
	$(BASELINE_COMPOSE) up -d

.PHONY: baseline-down
baseline-down: ## Stop the shared baseline stack
	$(BASELINE_COMPOSE) down

.PHONY: baseline-logs
baseline-logs: ## Follow logs for the shared baseline stack
	$(BASELINE_COMPOSE) logs -f

.PHONY: baseline-kibana
baseline-kibana: ## Bring Kibana up alongside the baseline (it is scaled to 0 by default)
	$(BASELINE_COMPOSE) up -d --scale kibana=1 kibana

.PHONY: sandbox-up
sandbox-up: guard-NAME guard-SERVICE ## Run a service on the dev host instead of your laptop (compiled services, unattended): NAME= SERVICE= [ISOLATED=1 own Postgres + prefixed ES] [BAKED=1 no source mount]
ifdef ISOLATED
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) up -d --wait sbx-postgres
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) run --rm --no-deps sbx-write-migrate
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) run --rm --no-deps sbx-read-migrate
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) run --rm --no-deps sbx-read-es-init
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) run --rm --no-deps sbx-ai-migrate
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) run --rm --no-deps sbx-webhook-migrate
endif
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) build $(SANDBOX_SERVICE)
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) up -d --no-deps $(SANDBOX_SERVICE)
	@if ! echo "$(SANDBOX_HTTP_SERVICES)" | tr ' ' '\n' | grep -qx "$(SERVICE)"; then \
		echo "sandbox '$(NAME)': $(SERVICE) serves no HTTP — running it without a gateway route"; \
		exit 0; \
	fi; \
	address=""; \
	for attempt in 1 2 3 4 5 6 7 8 9 10; do \
		address=$$(docker inspect $(SANDBOX_CONTAINER) --format '$(SANDBOX_ADDRESS_FORMAT)' 2>/dev/null | tr -d '[:space:]'); \
		[ -n "$$address" ] && break; \
		sleep 1; \
	done; \
	if [ -z "$$address" ]; then \
		echo "Could not read the address of $(SANDBOX_CONTAINER) — is it running?"; \
		exit 1; \
	fi; \
	$(MAKE) --no-print-directory sandbox-route NAME=$(NAME) SERVICE=$(SERVICE) TARGET="$$address:$(SANDBOX_HTTP_PORT)"

.PHONY: sandbox-local
sandbox-local: guard-NAME guard-SERVICE guard-TARGET ## Route one service of a sandbox at a process on your laptop: NAME= SERVICE= TARGET=host.docker.internal:8100
	@$(MAKE) --no-print-directory sandbox-route NAME=$(NAME) SERVICE=$(SERVICE) TARGET=$(TARGET)

.PHONY: sandbox-tunnels
sandbox-tunnels: guard-DEV_HOST ## Open SSH tunnels from this laptop to the dev host: DEV_HOST= [DEV_HOST_USER=] [LOCAL_SERVICE_PORT=8100] [PRINT=1]
	@infrastructure/dev-host/open_tunnels.sh \
		"$(DEV_HOST)" "$(LOCAL_SERVICE_PORT)" "$(PRINT)" "$(DEV_HOST_USER)"

.PHONY: sandbox-env
sandbox-env: guard-NAME guard-SERVICE ## Write an env file pointing a locally-run service at the baseline: NAME= SERVICE= [DEV_HOST=]
	@set -a; [ -f .env ] && . ./.env; set +a; \
	written=$$(infrastructure/dev-host/generate_sandbox_env.sh \
		"$(NAME)" "$(SERVICE)" "$(DEV_HOST)" "$(SANDBOX_ENV_DIR)/$(NAME)-$(SERVICE).env"); \
	echo "wrote $$written (endpoints: $(DEV_HOST))"; \
	echo "run the service with:  set -a; . $$written; set +a; <your run command>"

.PHONY: sandbox-route
sandbox-route: guard-NAME guard-SERVICE guard-TARGET ## Register the upstream one service of a sandbox routes to
	@$(REDIS_IN_BASELINE) SET $(SANDBOX_ROUTE_KEY) "$(TARGET)" EX $(SANDBOX_ROUTE_TTL_SECONDS) >/dev/null
	@echo "sandbox '$(NAME)' $(SERVICE) -> $(TARGET)"

.PHONY: sandbox-down
sandbox-down: guard-NAME ## Remove a sandbox's containers and its gateway route
	-SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) $(SANDBOX_COMPOSE) down --remove-orphans --volumes
	-@keys=$$($(REDIS_IN_BASELINE) --scan --pattern '$(SANDBOX_ROUTE_KEY_PREFIX)$(NAME):*' | tr -d '\r'); \
	for key in $$keys; do \
		$(REDIS_IN_BASELINE) DEL "$$key" < /dev/null >/dev/null; \
	done
	@echo "sandbox '$(NAME)' removed"

.PHONY: sandbox-list
sandbox-list: ## List registered sandbox routes
	@keys=$$($(REDIS_IN_BASELINE) --scan --pattern '$(SANDBOX_ROUTE_KEY_PREFIX)*' | tr -d '\r' | sort); \
	printf '%-14s %-30s %-24s %s\n' SANDBOX SERVICE TARGET TTL; \
	for key in $$keys; do \
		target=$$($(REDIS_IN_BASELINE) GET "$$key" < /dev/null | tr -d '\r'); \
		remaining=$$($(REDIS_IN_BASELINE) TTL "$$key" < /dev/null | tr -d '\r'); \
		identity=$${key#$(SANDBOX_ROUTE_KEY_PREFIX)}; \
		printf '%-14s %-30s %-24s %ss\n' "$${identity%%:*}" "$${identity#*:}" "$$target" "$$remaining"; \
	done

.PHONY: sandbox-restart
sandbox-restart: guard-NAME guard-SERVICE ## Restart a sandbox container so a worker picks up live-mounted changes
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) restart $(SANDBOX_SERVICE)

.PHONY: sandbox-prune
sandbox-prune: ## Drop gateway routes whose sandbox container is gone
	@infrastructure/dev-host/prune_sandbox_routes.sh \
		"$(SANDBOX_ROUTE_KEY_PREFIX)" "$(BASELINE_PROJECT)"

.PHONY: sandbox-logs
sandbox-logs: guard-NAME ## Follow logs for a sandbox's containers
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) $(SANDBOX_COMPOSE) logs -f
