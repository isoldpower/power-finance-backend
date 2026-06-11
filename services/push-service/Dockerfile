# syntax=docker/dockerfile:1.7

# Build context MUST be the repository root — push-service depends on
# `kafka-client-go` from libraries/ via a local replace directive. Run from
# repo root:
#   docker build -f services/push-service/Dockerfile -t push-service .
# Or via the bundled compose.yaml (which sets context: ../..).

ARG GO_VERSION=1.26

# ---------- builder stage ----------
FROM golang:${GO_VERSION}-alpine AS builder

# GOWORK=off keeps the build hermetic: only the service module and the
# libraries its go.mod replaces point at are needed, not the whole
# workspace listed in go.work.
ENV CGO_ENABLED=0 \
    GOWORK=off

WORKDIR /src

# Layer 1: dependency download, cached until any go.mod/go.sum changes.
COPY libraries/kafka-client-go/go.mod libraries/kafka-client-go/go.sum libraries/kafka-client-go/
COPY services/push-service/go.mod services/push-service/go.sum services/push-service/
RUN --mount=type=cache,target=/go/pkg/mod \
    cd services/push-service && go mod download

# Layer 2: copy source and compile a static binary.
COPY libraries/kafka-client-go libraries/kafka-client-go
COPY services/push-service services/push-service
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    cd services/push-service && go build -trimpath -o /out/push-service ./cmd


# ---------- runtime stage ----------
FROM alpine:3.21 AS runtime

RUN addgroup -S -g 1000 app \
 && adduser -S -u 1000 -G app -s /sbin/nologin app

COPY --from=builder /out/push-service /usr/local/bin/push-service

USER app

EXPOSE 8001

# Exec form makes the binary PID 1 so docker's SIGTERM reaches it directly;
# the server's NotifyContext(SIGINT, SIGTERM) then shuts down gracefully and
# the Kafka consumer loop drains via its cancelled context.
ENTRYPOINT ["/usr/local/bin/push-service"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-push-service" \
      org.opencontainers.image.description="SSE push notifications fed by the events.async Kafka topic."
