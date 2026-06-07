# Power Finance — CQRS workspace Makefile.
#
# All targets assume the workspace root (this directory) as the working
# directory. Run `make help` for a list of available targets.
#
# The pre-commit git hook is auto-installed on every Makefile invocation:
# every real target order-only-depends on `.git/hooks/pre-commit`, which is
# materialised by `uv run pre-commit install`. First call wires the hook;
# subsequent calls are no-ops.

.DEFAULT_GOAL := help

# Some shells / hooks export a stale VIRTUAL_ENV which collides with the
# workspace venv at ./.venv. Unexport so `uv` falls back to project
# discovery from the working directory.
unexport VIRTUAL_ENV

WRITE_SERVICE_DIR   := services/write-service
READ_SERVICE_DIR    := services/read-service
CORRELATION_LIB_DIR := libraries/correlation-py
KAFKA_CLIENT_LIB_DIR := libraries/kafka-client-py
SAGA_LIB_DIR         := libraries/saga-pattern-py
READ_AT_LEAST_LIB_DIR := libraries/read-at-least-py

UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000

PRECOMMIT_CONFIG := .pre-commit.yaml
HOOK_SENTINEL    := .git/hooks/pre-commit

ROUTER_TARGETS := write read
ROUTING        := $(filter $(firstword $(MAKECMDGOALS)),$(ROUTER_TARGETS))

# -----------------------------------------------------------------------------
# Auto-install pre-commit hook (order-only prereq for every real target)
# -----------------------------------------------------------------------------

# Materialised by `pre-commit install`. Rebuilt when the config changes
# (sentinel becomes older than the config file).
$(HOOK_SENTINEL): $(PRECOMMIT_CONFIG)
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $@

# -----------------------------------------------------------------------------
# Per-service subcommand routing
# -----------------------------------------------------------------------------
# Usage: `make <service> <subcommand> [more args]` is rewritten to
#   `make -C services/<service>-service <subcommand> [more args]`.
# Examples:
#   make write build-image
#   make write up
#   make read test help
#
# `make <service>` with no subcommand falls into the service Makefile's
# default goal (its `help`).
#
# Implementation: when the FIRST goal on the command line is a router
# target, the root-level non-router targets below are skipped (wrapped
# in `ifeq ($(ROUTING),)`). This prevents collisions between root names
# (`help`, `test`, `lint`, …) and identical service subcommand names.
# To use root targets, drop the router prefix: `make help` not
# `make write help` (which means "run write-service's help").

.PHONY: write
write: | $(HOOK_SENTINEL) ## Route to write-service Makefile: `make write <subcommand>`
	@$(MAKE) -C $(WRITE_SERVICE_DIR) $(ROUTED_ARGS)

.PHONY: read
read: | $(HOOK_SENTINEL) ## Route to read-service Makefile: `make read <subcommand>`
	@$(MAKE) -C $(READ_SERVICE_DIR) $(ROUTED_ARGS)

# When routing, expose the trailing args to the recipe AND no-op them as
# Make goals so Make doesn't try to build them after the recipe returns.
ifneq ($(ROUTING),)
  ROUTED_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(ROUTED_ARGS):;@:)
endif

# -----------------------------------------------------------------------------
# Root-level targets — only defined when NOT routing to a service.
# Wrapping in `ifeq ($(ROUTING),)` avoids "overriding commands for target"
# warnings when a service subcommand shares a name with a root target.
# -----------------------------------------------------------------------------

ifeq ($(ROUTING),)

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# -----------------------------------------------------------------------------
# Workspace setup
# -----------------------------------------------------------------------------

.PHONY: install
install: ## Sync the uv workspace + wire git pre-commit hook
	uv sync --all-packages --group dev
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $(HOOK_SENTINEL)

.PHONY: clean
clean: | $(HOOK_SENTINEL) ## Remove __pycache__ and bytecode artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

.PHONY: test
test: test-correlation test-libraries test-write test-read ## Run every test suite

.PHONY: test-correlation
test-correlation: | $(HOOK_SENTINEL) ## Run correlation-py library tests (unittest)
	uv run python -m unittest discover -s $(CORRELATION_LIB_DIR)/correlation/__tests__ -t $(CORRELATION_LIB_DIR)

.PHONY: test-libraries
test-libraries: | $(HOOK_SENTINEL) ## Run the pytest library suites (kafka-client, saga, read-at-least)
	cd $(KAFKA_CLIENT_LIB_DIR) && uv run pytest -q
	cd $(SAGA_LIB_DIR) && uv run pytest -q
	cd $(READ_AT_LEAST_LIB_DIR) && uv run pytest -q

.PHONY: test-write
test-write: | $(HOOK_SENTINEL) ## Run Write Service tests (Django runner, postgres-write on host port 5433)
	cd $(WRITE_SERVICE_DIR) && uv run python manage.py test \
		--settings=write_service.settings.test

.PHONY: test-read
test-read: | $(HOOK_SENTINEL) ## Run Read Service tests (pytest, postgres-read on host port 5434)
	cd $(READ_SERVICE_DIR) && uv run pytest -q

# -----------------------------------------------------------------------------
# Lint / format / typecheck
# -----------------------------------------------------------------------------

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

.PHONY: typecheck
typecheck: | $(HOOK_SENTINEL) ## Run mypy against services + libraries
	uv run mypy services libraries

# -----------------------------------------------------------------------------
# Pre-commit
# -----------------------------------------------------------------------------

.PHONY: precommit-install
precommit-install: ## Force-reinstall the git pre-commit hook
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $(HOOK_SENTINEL)

.PHONY: precommit
precommit: | $(HOOK_SENTINEL) ## Run all pre-commit hooks against the entire tree
	uv run pre-commit run --config $(PRECOMMIT_CONFIG) --all-files

endif  # ifeq ($(ROUTING),)
