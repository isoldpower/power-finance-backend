# syntax=docker/dockerfile:1.7

# Build context MUST be the repository root — read-service is a uv workspace
# member that depends on `kafka-client-py` and `kafka-messages-proto` from
# libraries/. Run from repo root:
#   docker build -f services/read-service/Dockerfile -t read-service .
# Or via the bundled compose.yaml (which sets context: ../..).
#
# One image, multiple process types: the default CMD runs the ASGI web app;
# the compose stack overrides `command:` to run the Kafka consumer worker.

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5

# ---------- builder stage ----------
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Layer 1: install workspace dependencies only (no project source).
# Mounting the manifests as bind volumes keeps them out of the resulting
# layer — they're re-copied with the rest of the source in Layer 2.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=services/read-service/pyproject.toml,target=services/read-service/pyproject.toml \
    --mount=type=bind,source=libraries/kafka-client-py/pyproject.toml,target=libraries/kafka-client-py/pyproject.toml \
    --mount=type=bind,source=libraries/kafka-messages-proto/pyproject.toml,target=libraries/kafka-messages-proto/pyproject.toml \
    --mount=type=bind,source=libraries/saga-pattern-py/pyproject.toml,target=libraries/saga-pattern-py/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --package read-service

# Layer 2: copy source for the service + every workspace lib it imports,
# then install the project itself (editable install registers entrypoints).
COPY libraries/kafka-client-py /app/libraries/kafka-client-py
COPY libraries/saga-pattern-py /app/libraries/saga-pattern-py
COPY libraries/kafka-messages-proto /app/libraries/kafka-messages-proto
COPY services/read-service /app/services/read-service
COPY pyproject.toml uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package read-service


# ---------- runtime stage ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

# psycopg[binary] bundles libpq; no system libpq needed. Curl is for the
# container healthcheck on the web process type.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Non-root user — nothing is written under /app at runtime.
RUN groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

# PYTHONUNBUFFERED keeps the async consumer's stdout/stderr flushing in real
# time under docker logs; PYTHONDONTWRITEBYTECODE avoids cache writes as the
# non-root user.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=read_service.settings.production

WORKDIR /app/services/read-service

USER app

EXPOSE 8000

# Default process type: the ASGI web app. The consumer worker overrides this
# via `command:` in compose. Exec form makes the process PID 1 so SIGTERM
# reaches it directly — the consumer's SigtermShutdownSignal then drains and
# stops the loop gracefully.
CMD ["uvicorn", "read_service.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-read-service" \
      org.opencontainers.image.description="CQRS read side (projections, caches, Kafka consumers)."
