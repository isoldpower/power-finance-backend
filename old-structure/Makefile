.PHONY: test test-fast test-integration restart rebuild

# Variables
PYTHON = .venv/bin/python
MANAGE = power_finance/manage.py
SETTINGS = power_finance.settings
PORT ?= 8000
SERVICES = django celery-worker celery-beat

# Run all tests
test:
	$(PYTHON) $(MANAGE) test \
		finances.domain.tests \
		finances.application.use_cases.commands.tests \
		finances.application.use_cases.queries.tests \
		finances.presentation.tests \
		environment.domain.tests \
		environment.application.tests \
		environment.presentation.tests \
		--settings=$(SETTINGS)

# Run fast unit tests (domain and application layer, no DB)
test-fast:
	$(PYTHON) $(MANAGE) test \
		finances.domain.tests \
		finances.application.use_cases.commands.tests \
		finances.application.use_cases.queries.tests \
		environment.domain.tests \
		environment.application.tests \
		--settings=$(SETTINGS)

# Run integration tests (presentation layer)
test-integration:
	$(PYTHON) $(MANAGE) test \
		finances.presentation.tests \
		environment.presentation.tests \
		--settings=$(SETTINGS)

# Restart app services without rebuilding
restart:
	docker compose restart $(SERVICES)

# Rebuild and restart app services
rebuild:
	docker compose up -d --build $(SERVICES)

# Run the ASGI server with hot reload on file changes
run-dev:
	cd power_finance && \
	../$(PYTHON) -m uvicorn power_finance.asgi:application \
		--reload --port $(PORT)

# Run the ASGI server in stable mode without reloads
run-stable:
	cd power_finance && \
	../$(PYTHON) -m gunicorn power_finance.asgi:application -k uvicorn_worker.UvicornWorker
