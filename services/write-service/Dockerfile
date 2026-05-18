# syntax=docker/dockerfile:1.7

# Build context MUST be the repository root — the write-service is a uv
# workspace member that depends on `correlation-py` from libraries/.
# Run from repo root:
#   docker build -f services/write-service/Dockerfile -t write-service .
# Or via the bundled compose.yaml (which sets context: ../..).

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
    --mount=type=bind,source=services/write-service/pyproject.toml,target=services/write-service/pyproject.toml \
    --mount=type=bind,source=libraries/correlation-py/pyproject.toml,target=libraries/correlation-py/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --package write-service

# Layer 2: copy source for the service + every workspace lib it imports,
# then install the project itself (editable install registers entrypoints).
COPY libraries/correlation-py /app/libraries/correlation-py
COPY services/write-service /app/services/write-service
COPY pyproject.toml uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package write-service


# ---------- runtime stage ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

# psycopg[binary] bundles libpq; no system libpq needed. Curl is for the
# container healthcheck.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Non-root user — Django writes nothing under /app at runtime (static
# files are served by the gateway) so a read-only-ish layout is fine.
RUN groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=write_service.settings.production

WORKDIR /app/services/write-service

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "write_service.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-write-service" \
      org.opencontainers.image.description="CQRS write side (Postgres + outbox + ImmuDB)."
