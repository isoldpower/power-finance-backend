# syntax=docker/dockerfile:1.7
# See ./README.md → "Build & Docker"

ARG GO_VERSION=1.26

FROM golang:${GO_VERSION}-alpine AS builder

ENV CGO_ENABLED=0 \
    GOWORK=off

WORKDIR /src

COPY libraries/kafka-client-go/go.mod libraries/kafka-client-go/go.sum libraries/kafka-client-go/
COPY libraries/kafka-messages-proto/go.mod libraries/kafka-messages-proto/go.sum libraries/kafka-messages-proto/
COPY services/webhook-service/go.mod services/webhook-service/go.sum services/webhook-service/
RUN --mount=type=cache,target=/go/pkg/mod \
    cd services/webhook-service && go mod download

COPY libraries/kafka-client-go libraries/kafka-client-go
COPY libraries/kafka-messages-proto libraries/kafka-messages-proto
COPY services/webhook-service services/webhook-service
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    cd services/webhook-service && go build -trimpath -o /out/webhook-service ./cmd


FROM alpine:3.21 AS runtime

RUN addgroup -S -g 1000 app \
 && adduser -S -u 1000 -G app -s /sbin/nologin app

COPY --from=builder /out/webhook-service /usr/local/bin/webhook-service

USER app

EXPOSE 8002

ENTRYPOINT ["/usr/local/bin/webhook-service"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-webhook-service" \
      org.opencontainers.image.description="Consumes events.async, delivers signed webhooks, owns its Postgres."
