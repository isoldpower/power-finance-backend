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
CORRELATION_LIB_DIR := libraries/correlation-py

UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000

PRECOMMIT_CONFIG := .pre-commit.yaml
HOOK_SENTINEL    := .git/hooks/pre-commit

# -----------------------------------------------------------------------------
# Auto-install pre-commit hook (order-only prereq for every real target)
# -----------------------------------------------------------------------------

# Materialised by `pre-commit install`. Rebuilt when the config changes
# (sentinel becomes older than the config file).
$(HOOK_SENTINEL): $(PRECOMMIT_CONFIG)
	uv run pre-commit install --config $(PRECOMMIT_CONFIG)
	@touch $@

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
# Services
# -----------------------------------------------------------------------------

.PHONY: run-write
run-write: | $(HOOK_SENTINEL) ## Start the Write Service with uvicorn (autoreload)
	cd $(WRITE_SERVICE_DIR) && uv run uvicorn write_service.asgi:application \
		--reload --host $(UVICORN_HOST) --port $(UVICORN_PORT)

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

.PHONY: test
test: test-correlation test-write ## Run every test suite

.PHONY: test-correlation
test-correlation: | $(HOOK_SENTINEL) ## Run correlation-py library tests
	uv run python -m unittest discover -s $(CORRELATION_LIB_DIR)/tests -t $(CORRELATION_LIB_DIR)

.PHONY: test-write
test-write: | $(HOOK_SENTINEL) ## Run Write Service tests (sqlite, hermetic)
	cd $(WRITE_SERVICE_DIR) && uv run python manage.py test \
		--settings=write_service.settings.test

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
