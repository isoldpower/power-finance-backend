# What is being ran in case the user called Makefile without command(last) argument.
.DEFAULT_GOAL := help
# Separate test database URL used to protect user data from testing seed.
AI_TEST_DATABASE_URL ?= postgresql+psycopg://postgres:postgres@localhost:5436/power_finance_ai_test
# Docker compose target.
COMPOSE := docker compose -f compose.yaml


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
test: ## Run AI Service tests (postgres-ai on host port 5436)
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
