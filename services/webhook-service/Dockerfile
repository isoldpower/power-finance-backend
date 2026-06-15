# syntax=docker/dockerfile:1.7

# Build context MUST be the repository root — webhook-service depends on
# `kafka-client-go` and `kafka-messages-proto` from libraries/ via local
# replace directives. Run from repo root:
#   docker build -f services/webhook-service/Dockerfile -t webhook-service .
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
COPY libraries/kafka-messages-proto/go.mod libraries/kafka-messages-proto/go.sum libraries/kafka-messages-proto/
COPY services/webhook-service/go.mod services/webhook-service/go.sum services/webhook-service/
RUN --mount=type=cache,target=/go/pkg/mod \
    cd services/webhook-service && go mod download

# Layer 2: copy source and compile a static binary.
COPY libraries/kafka-client-go libraries/kafka-client-go
COPY libraries/kafka-messages-proto libraries/kafka-messages-proto
COPY services/webhook-service services/webhook-service
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    cd services/webhook-service && go build -trimpath -o /out/webhook-service ./cmd


# ---------- runtime stage ----------
FROM alpine:3.21 AS runtime

RUN addgroup -S -g 1000 app \
 && adduser -S -u 1000 -G app -s /sbin/nologin app

COPY --from=builder /out/webhook-service /usr/local/bin/webhook-service

USER app

EXPOSE 8002

# Exec form makes the binary PID 1 so docker's SIGTERM reaches it directly;
# the server's NotifyContext(SIGINT, SIGTERM) then shuts down gracefully and
# the Kafka consumer loop + retry scheduler drain via their cancelled context.
ENTRYPOINT ["/usr/local/bin/webhook-service"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-webhook-service" \
      org.opencontainers.image.description="Consumes events.async, delivers signed webhooks, owns its Postgres."
