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
	@awk 'BEGIN {FS = ":.*?## "} \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5); next } \
		/^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

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
test: test-correlation test-libraries test-write test-read test-ai test-go test-java test-contract test-gateway ## Run every test suite

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
test-write: | $(HOOK_SENTINEL) ## Run Write Service tests (pytest; needs `make test-datastores`, port 5533)
	cd $(WRITE_SERVICE_DIR) && uv run pytest -q

.PHONY: test-read
test-read: | $(HOOK_SENTINEL) ## Run Read Service tests (pytest; needs `make test-datastores`, port 5534)
	cd $(READ_SERVICE_DIR) && uv run pytest -q

.PHONY: test-ai
test-ai: | $(HOOK_SENTINEL) ## Run AI Service tests (pytest; needs `make test-datastores`, port 5536)
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

.PHONY: test-gateway
test-gateway: ## Run the Kong plugin specs under the gateway's own LuaJIT (needs Docker)
	@infrastructure/kong/run_plugin_tests.sh

# Disposable, tmpfs-backed, and deliberately off the ports `devhost-tunnels` forwards,
# so a suite can never reach the dev host's databases. Safe to leave running.
.PHONY: test-datastores
test-datastores: ## Start the throwaway Postgres instances the Python suites expect (5533/5534/5536)
	$(TEST_DATASTORES_COMPOSE) up -d --wait

.PHONY: test-datastores-down
test-datastores-down: ## Stop them and discard their data
	$(TEST_DATASTORES_COMPOSE) down --remove-orphans

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
# No env layering: the test databases take the plain credentials the suites default to,
# never the dev host's, which is what a laptop .env carries.
TEST_DATASTORES_COMPOSE := docker compose -f compose.test-datastores.yaml

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
# The port each service's edge listens on when run natively on a laptop, mirroring
# the PORT default in that service's own Makefile. A route registered for one
# service must reach that service: pointing ai-service at 8100 lands on
# read-service, which answers, so the mistake looks like a routing success.
SANDBOX_LOCAL_PORT_read-service  := 8100
SANDBOX_LOCAL_PORT_ai-service    := 8101
SANDBOX_LOCAL_PORT_write-service := 8102
SANDBOX_LOCAL_PORTS              := 8100 8101 8102
LOCAL_SERVICE_PORT       ?= $(SANDBOX_LOCAL_PORT_$(SERVICE))
# Every laptop port is forwarded unless one is named, so routing a second service
# does not need the tunnels reopened.
LOCAL_SERVICE_PORTS      ?= $(if $(filter command line environment,$(origin LOCAL_SERVICE_PORT)),$(LOCAL_SERVICE_PORT),$(SANDBOX_LOCAL_PORTS))
# The dev host account is rarely your laptop account; ssh defaults to the latter.
DEV_HOST_USER            ?=
DEV_HOST_REPO            ?= ~/daemons/power-finance-backend

# The laptop's own datastores for an isolated sandbox. Project name carries the
# sandbox, so two of them on one machine keep separate volumes.
SANDBOX_LOCAL_DATASTORES = $(COMPOSE) -p pf-sbx-$(NAME) -f compose.sandbox-local-datastores.yaml
SANDBOX_DATABASE_PORT   ?= 5633

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
# From a laptop the gateway reaches your service back down the -R tunnel that
# `devhost-tunnels` opened, which lands on the dev host's own loopback.
SANDBOX_REMOTE_TARGET = $(or $(TARGET),$(if $(LOCAL_SERVICE_PORT),host.docker.internal:$(LOCAL_SERVICE_PORT)))

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

##@ Dev host — run these ON the dev host

.PHONY: host-build
host-build: ## Build every baseline image, one per tag (safe to re-run; cached)
	$(BASELINE_COMPOSE) build $(BASELINE_BUILD_SERVICES)

.PHONY: host-up
host-up: host-build ## Start the shared baseline stack on the dev host (tuned, Kibana off, Jaeger on)
	$(BASELINE_COMPOSE) up -d

.PHONY: host-down
host-down: ## Stop the shared baseline stack
	$(BASELINE_COMPOSE) down

.PHONY: host-logs
host-logs: ## Follow logs for the shared baseline stack
	$(BASELINE_COMPOSE) logs -f

.PHONY: host-kibana
host-kibana: ## Bring Kibana up alongside the baseline (it is scaled to 0 by default)
	$(BASELINE_COMPOSE) up -d --scale kibana=1 kibana

.PHONY: host-sandbox-up
host-sandbox-up: guard-NAME guard-SERVICE ## Run a service on the dev host instead of your laptop (compiled services, unattended): NAME= SERVICE= [ISOLATED=1 own Postgres + prefixed ES] [BAKED=1 no source mount]
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
	$(MAKE) --no-print-directory host-route NAME=$(NAME) SERVICE=$(SERVICE) TARGET="$$address:$(SANDBOX_HTTP_PORT)"

.PHONY: host-sandbox-down
host-sandbox-down: guard-NAME ## Remove a sandbox's containers and its gateway route
	-SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) $(SANDBOX_COMPOSE) down --remove-orphans --volumes
	-@keys=$$($(REDIS_IN_BASELINE) --scan --pattern '$(SANDBOX_ROUTE_KEY_PREFIX)$(NAME):*' | tr -d '\r'); \
	for key in $$keys; do \
		$(REDIS_IN_BASELINE) DEL "$$key" < /dev/null >/dev/null; \
	done
	@echo "sandbox '$(NAME)' removed"

.PHONY: host-sandbox-restart
host-sandbox-restart: guard-NAME guard-SERVICE ## Restart a sandbox container so a worker picks up live-mounted changes
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) \
		$(SANDBOX_COMPOSE) restart $(SANDBOX_SERVICE)

.PHONY: host-sandbox-logs
host-sandbox-logs: guard-NAME ## Follow logs for a sandbox's containers
	SANDBOX_ID=$(NAME) BASELINE_NETWORK_NAME=$(BASELINE_NETWORK_NAME) $(SANDBOX_COMPOSE) logs -f

# Routes live in the baseline's Redis, so this runs where the baseline runs — on the
# dev host. From a laptop, invoke it over ssh (see the hint below).
.PHONY: host-route
host-route: guard-NAME guard-SERVICE guard-TARGET ## Register the upstream one service of a sandbox routes to
	@if ! docker ps --filter "name=$(BASELINE_PROJECT)-gateway-redis" --format '{{.Names}}' | grep -q .; then \
		echo "The baseline is not running here, so there is no route store to write to."; \
		echo "Route registration happens on the dev host. From a laptop:"; \
		echo ""; \
		echo "  make devhost-route NAME=$(NAME) SERVICE=$(SERVICE) \\"; \
		echo "      TARGET=$(TARGET) DEV_HOST=<dev-host>"; \
		echo ""; \
		echo "or by hand:"; \
		echo ""; \
		echo "  ssh <user>@<dev-host> 'cd <repo> && make host-route \\"; \
		echo "      NAME=$(NAME) SERVICE=$(SERVICE) TARGET=$(TARGET)'"; \
		echo ""; \
		exit 1; \
	fi
	@$(REDIS_IN_BASELINE) SET $(SANDBOX_ROUTE_KEY) "$(TARGET)" EX $(SANDBOX_ROUTE_TTL_SECONDS) >/dev/null
	@echo "sandbox '$(NAME)' $(SERVICE) -> $(TARGET)"

.PHONY: host-route-laptop
host-route-laptop: guard-NAME guard-SERVICE guard-TARGET ## Route one service of a sandbox at a process on your laptop: NAME= SERVICE= TARGET=host.docker.internal:8100
	@$(MAKE) --no-print-directory host-route NAME=$(NAME) SERVICE=$(SERVICE) TARGET=$(TARGET)

.PHONY: host-unroute
host-unroute: guard-NAME guard-SERVICE ## Drop one service's sandbox route, sending it back to the baseline
	@if ! docker ps --filter "name=$(BASELINE_PROJECT)-gateway-redis" --format '{{.Names}}' | grep -q .; then \
		echo "The baseline is not running here, so there is no route store to write to."; \
		echo "From a laptop:"; \
		echo ""; \
		echo "  make devhost-unroute NAME=$(NAME) SERVICE=$(SERVICE) DEV_HOST=<dev-host>"; \
		echo ""; \
		exit 1; \
	fi
	@removed=$$($(REDIS_IN_BASELINE) DEL $(SANDBOX_ROUTE_KEY) | tr -d '\r'); \
	if [ "$$removed" = "0" ]; then \
		echo "sandbox '$(NAME)' had no $(SERVICE) route; nothing to drop"; \
	else \
		echo "sandbox '$(NAME)' $(SERVICE) -> baseline (route dropped)"; \
	fi

.PHONY: host-list
host-list: ## List registered sandbox routes
	@keys=$$($(REDIS_IN_BASELINE) --scan --pattern '$(SANDBOX_ROUTE_KEY_PREFIX)*' | tr -d '\r' | sort); \
	printf '%-14s %-30s %-24s %s\n' SANDBOX SERVICE TARGET TTL; \
	for key in $$keys; do \
		target=$$($(REDIS_IN_BASELINE) GET "$$key" < /dev/null | tr -d '\r'); \
		remaining=$$($(REDIS_IN_BASELINE) TTL "$$key" < /dev/null | tr -d '\r'); \
		identity=$${key#$(SANDBOX_ROUTE_KEY_PREFIX)}; \
		printf '%-14s %-30s %-24s %ss\n' "$${identity%%:*}" "$${identity#*:}" "$$target" "$$remaining"; \
	done

.PHONY: host-prune
host-prune: ## Drop gateway routes whose sandbox container is gone
	@infrastructure/dev-host/prune_sandbox_routes.sh \
		"$(SANDBOX_ROUTE_KEY_PREFIX)" "$(BASELINE_PROJECT)"

# Everything a sandbox owns, in one go: its containers, the routes that divert HTTP to
# it, and the consumer groups that divert events to it. Afterwards `X-Sandbox: <name>`
# is indistinguishable from sending no header.
.PHONY: host-wipe
host-wipe: guard-NAME ## Remove a sandbox entirely — containers, routes and consumer groups: NAME= [FORCE=1]
	@infrastructure/dev-host/wipe_sandbox.sh \
		"$(NAME)" "$(SANDBOX_ROUTE_KEY_PREFIX)" "$(BASELINE_PROJECT)" \
		"$(SANDBOX_PROJECT_PREFIX)$(NAME)" "$(FORCE)"

# Only for a sandbox that ran ISOLATED: it applied the events it claimed into its own
# datastores, so the baseline's read model never saw them. A shared sandbox needs
# nothing — its consumer wrote into the baseline's stores on the baseline's behalf.
.PHONY: host-replay
host-replay: guard-NAME ## Give a finished isolated sandbox's events back to the baseline read model: NAME= [DRY_RUN=1] [SINCE=] [UNTIL=]
	@infrastructure/dev-host/replay_sandbox_events.sh \
		"$(NAME)" "$(BASELINE_PROJECT)" "$(DRY_RUN)" "$(SINCE)" "$(UNTIL)"

##@ Dev host, driven from your laptop — these reach it over ssh

.PHONY: devhost-tunnels
devhost-tunnels: guard-DEV_HOST ## Open SSH tunnels from this laptop to the dev host: DEV_HOST= [DEV_HOST_USER=] [LOCAL_SERVICE_PORTS=8100 8101 8102] [PRINT=1]
	@infrastructure/dev-host/open_tunnels.sh \
		"$(DEV_HOST)" "$(LOCAL_SERVICE_PORTS)" "$(PRINT)" "$(DEV_HOST_USER)"

# The laptop-side companion to host-route: same registration, one ssh hop away.
.PHONY: devhost-route
devhost-route: guard-NAME guard-SERVICE guard-DEV_HOST ## Register a sandbox route on the dev host from your laptop: NAME= SERVICE= DEV_HOST= [TARGET=host.docker.internal:<service's port>] [DEV_HOST_USER=] [DEV_HOST_REPO=~/daemons/power-finance-backend]
	@if [ -z "$(SANDBOX_REMOTE_TARGET)" ]; then \
		echo "No laptop port is known for '$(SERVICE)', so there is nothing to route to."; \
		echo "Services with a laptop runner: read-service ai-service write-service."; \
		echo "For anything else, name the upstream yourself:"; \
		echo ""; \
		echo "  make devhost-route NAME=$(NAME) SERVICE=$(SERVICE) \\"; \
		echo "      DEV_HOST=$(DEV_HOST) TARGET=host.docker.internal:<port>"; \
		echo ""; \
		exit 1; \
	fi
	@infrastructure/dev-host/run_remote_make.sh \
		"$(DEV_HOST)" "$(DEV_HOST_USER)" "$(DEV_HOST_REPO)" \
		host-route "NAME=$(NAME)" "SERVICE=$(SERVICE)" "TARGET=$(SANDBOX_REMOTE_TARGET)"

# The inverse of devhost-route: the route goes, the service falls back to the
# baseline. Leaves containers and consumer groups alone — see `host-sandbox-down` for those.
.PHONY: devhost-unroute
devhost-unroute: guard-NAME guard-SERVICE guard-DEV_HOST ## Drop a sandbox route on the dev host from your laptop: NAME= SERVICE= DEV_HOST= [DEV_HOST_USER=] [DEV_HOST_REPO=~/daemons/power-finance-backend]
	@infrastructure/dev-host/run_remote_make.sh \
		"$(DEV_HOST)" "$(DEV_HOST_USER)" "$(DEV_HOST_REPO)" \
		host-unroute "NAME=$(NAME)" "SERVICE=$(SERVICE)"

.PHONY: devhost-replay
devhost-replay: guard-NAME guard-DEV_HOST ## Replay a finished isolated sandbox's events into the baseline, from your laptop: NAME= DEV_HOST= [DRY_RUN=1]
	@infrastructure/dev-host/run_remote_make.sh \
		"$(DEV_HOST)" "$(DEV_HOST_USER)" "$(DEV_HOST_REPO)" \
		host-replay "NAME=$(NAME)" "DRY_RUN=$(DRY_RUN)" "SINCE=$(SINCE)" "UNTIL=$(UNTIL)"

.PHONY: devhost-wipe
devhost-wipe: guard-NAME guard-DEV_HOST ## Remove a sandbox entirely, from your laptop: NAME= DEV_HOST= [FORCE=1] [DEV_HOST_USER=] [DEV_HOST_REPO=]
	@infrastructure/dev-host/run_remote_make.sh \
		"$(DEV_HOST)" "$(DEV_HOST_USER)" "$(DEV_HOST_REPO)" \
		host-wipe "NAME=$(NAME)" "FORCE=$(FORCE)"

##@ Local sandbox — run these on your laptop

.PHONY: sandbox-env
sandbox-env: guard-NAME guard-SERVICE ## Write an env file pointing a locally-run service at the baseline: NAME= SERVICE= [DEV_HOST=] [ISOLATED=1 own Postgres + prefixed ES]
	@set -a; [ -f .env ] && . ./.env; set +a; \
	SANDBOX_DATABASE_PORT=$(SANDBOX_DATABASE_PORT) \
	written=$$(infrastructure/dev-host/generate_sandbox_env.sh \
		"$(NAME)" "$(SERVICE)" "$(DEV_HOST)" "$(SANDBOX_ENV_DIR)/$(NAME)-$(SERVICE).env" "$(ISOLATED)"); \
	echo "wrote $$written (endpoints: $(DEV_HOST)$(if $(ISOLATED), — database: localhost:$(SANDBOX_DATABASE_PORT),))"; \
	$(if $(ISOLATED),echo "start that database with:  make sandbox-datastores NAME=$(NAME)";,) \
	echo "run the service with:  set -a; . $$written; set +a; <your run command>"

# The laptop half of ISOLATED=1. compose.sandbox-datastores.yaml does this for a
# sandbox running on the dev host; this does it for one running here.
.PHONY: sandbox-datastores
sandbox-datastores: guard-NAME ## Start this laptop's own Postgres for an isolated sandbox and migrate every service: NAME= [SANDBOX_DATABASE_PORT=5633]
	@SANDBOX_DATABASE_PORT=$(SANDBOX_DATABASE_PORT) $(SANDBOX_LOCAL_DATASTORES) up -d --wait sbx-postgres
	@# --build, because the point of an isolated sandbox is usually a migration that
	@# only exists in the working tree. Without it the prebuilt image runs whatever
	@# chain it was built with and reports success at the wrong revision.
	@for job in sbx-write-migrate sbx-read-migrate sbx-ai-migrate sbx-webhook-migrate; do \
		echo "== $$job"; \
		SANDBOX_DATABASE_PORT=$(SANDBOX_DATABASE_PORT) \
			$(SANDBOX_LOCAL_DATASTORES) run --rm --no-deps --build "$$job" || exit 1; \
	done
	@echo "sandbox '$(NAME)' database ready on localhost:$(SANDBOX_DATABASE_PORT)"

.PHONY: sandbox-datastores-down
sandbox-datastores-down: guard-NAME ## Remove this laptop's isolated sandbox database AND its data: NAME=
	@SANDBOX_DATABASE_PORT=$(SANDBOX_DATABASE_PORT) $(SANDBOX_LOCAL_DATASTORES) down -v
	@echo "sandbox '$(NAME)' local database removed"
