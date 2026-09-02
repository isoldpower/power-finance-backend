# syntax=docker/dockerfile:1.7
# See ./README.md → "Build & Docker"
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim AS builder

COPY --from=uv /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=services/read-service/pyproject.toml,target=services/read-service/pyproject.toml \
    --mount=type=bind,source=libraries/kafka-client-py/pyproject.toml,target=libraries/kafka-client-py/pyproject.toml \
    --mount=type=bind,source=libraries/kafka-consumer-py/pyproject.toml,target=libraries/kafka-consumer-py/pyproject.toml \
    --mount=type=bind,source=libraries/kafka-messages-proto/pyproject.toml,target=libraries/kafka-messages-proto/pyproject.toml \
    --mount=type=bind,source=libraries/saga-pattern-py/pyproject.toml,target=libraries/saga-pattern-py/pyproject.toml \
    --mount=type=bind,source=libraries/read-at-least-py/pyproject.toml,target=libraries/read-at-least-py/pyproject.toml \
    --mount=type=bind,source=libraries/correlation-py/pyproject.toml,target=libraries/correlation-py/pyproject.toml \
    --mount=type=bind,source=libraries/filter-grammar-py/pyproject.toml,target=libraries/filter-grammar-py/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --package read-service

COPY libraries/kafka-client-py /app/libraries/kafka-client-py
COPY libraries/kafka-consumer-py /app/libraries/kafka-consumer-py
COPY libraries/saga-pattern-py /app/libraries/saga-pattern-py
COPY libraries/kafka-messages-proto /app/libraries/kafka-messages-proto
COPY libraries/read-at-least-py /app/libraries/read-at-least-py
COPY libraries/correlation-py /app/libraries/correlation-py
COPY libraries/filter-grammar-py /app/libraries/filter-grammar-py
COPY services/read-service /app/services/read-service
COPY pyproject.toml uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package read-service

FROM python:${PYTHON_VERSION}-slim AS runtime

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=read_service.settings.production

WORKDIR /app/services/read-service

USER app

EXPOSE 8000

CMD ["uvicorn", "read_service.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-read-service" \
      org.opencontainers.image.description="CQRS read side (projections, caches, Kafka consumers)."
