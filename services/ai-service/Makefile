# What is being ran in case the user called Makefile without command(last) argument.
.DEFAULT_GOAL := help
# Separate test database URL used to protect user data from testing seed.
# Port 5536, not 5436: the latter is the dev host's postgres-ai while sandbox tunnels
# are open. `make test-datastores` at the repo root starts what this expects.
AI_TEST_DATABASE_URL ?= postgresql+psycopg://postgres:postgres@localhost:5536/power_finance_ai_test
# Docker compose target.
COMPOSE := docker compose -f compose.yaml
REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))../..)
SANDBOX_RUNNER := $(REPO_ROOT)/infrastructure/dev-host/run_sandbox_service.sh
SANDBOX_NAME ?= $(NAME)
SANDBOX_ENV_FILE = $(REPO_ROOT)/.sandbox/$(SANDBOX_NAME)-ai-service.env
PORT ?= 8101
# The dispatcher is the half that books postings; running only the edge leaves
# every transaction in the sandbox without ledger entries.
AI_PROCESSES = \
	"edge=uv run uvicorn ai_service.main:app --port $(PORT) --reload" \
	"dispatcher=uv run python -m background_workers.main"
# The Kafka topics and group are this service's own settings, declared with no
# defaults, so they come from services/ai-service/.env rather than the sandbox file.
AI_REQUIRED = AI_DATABASE_URL KAFKA_BOOTSTRAP_SERVERS KAFKA_OUTBOX_TOPIC \
	KAFKA_AI_GROUP_ID KAFKA_RETRY_TOPIC KAFKA_DLQ_TOPIC LOG_LEVEL


.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: run
run: ## Run the posting dispatcher locally (needs Kafka + postgres-ai reachable from host)
	uv run python -m background_workers.main

.PHONY: serve
serve: ## Run the FastAPI app locally
	uv run uvicorn ai_service.main:app --reload

.PHONY: migrate
migrate: ## Apply every Alembic migration
	uv run alembic upgrade head

.PHONY: makemigration
makemigration: ## Autogenerate a migration from the models (pass NAME="...")
	uv run alembic revision --autogenerate -m "$(NAME)"

.PHONY: test
test: ## Run AI Service tests (needs `make test-datastores` at the repo root, port 5536)
	AI_DATABASE_URL="$(AI_TEST_DATABASE_URL)" uv run pytest -q

.PHONY: build-image
build-image: ## Build the AI Service Docker image (context = repo root)
	$(COMPOSE) build ai-service

.PHONY: up
up: ## Start the AI Service stack (ai-service + ai-dispatcher + postgres-ai + kafka)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop the AI Service stack (ai-service + ai-dispatcher + postgres-ai + kafka)
	$(COMPOSE) down

guard-NAME:
	@if [ -z "$(SANDBOX_NAME)" ]; then \
		echo "Missing required variable: NAME (the sandbox to run as)"; \
		exit 1; \
	fi

.PHONY: sandbox
sandbox: guard-NAME ## Run the whole service for a sandbox — edge + posting dispatcher: NAME= [PORT=8101] [ISOLATED=1]
	@$(if $(ISOLATED),$(MAKE) --no-print-directory -C $(REPO_ROOT) sandbox-datastores NAME=$(SANDBOX_NAME),:)
	@ISOLATED=$(ISOLATED) $(SANDBOX_RUNNER) "$(SANDBOX_ENV_FILE)" "$(REPO_ROOT)/services/ai-service/.env" "$(AI_REQUIRED)" $(AI_PROCESSES)
