# syntax=docker/dockerfile:1.7
# See ./README.md → "Build & Docker"

ARG GO_VERSION=1.26

FROM golang:${GO_VERSION}-alpine AS builder

ENV CGO_ENABLED=0 \
    GOWORK=off

WORKDIR /src

COPY libraries/kafka-client-go/go.mod libraries/kafka-client-go/go.sum libraries/kafka-client-go/
COPY services/push-service/go.mod services/push-service/go.sum services/push-service/
RUN --mount=type=cache,target=/go/pkg/mod \
    cd services/push-service && go mod download

COPY libraries/kafka-client-go libraries/kafka-client-go
COPY services/push-service services/push-service
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    cd services/push-service && go build -trimpath -o /out/push-service ./cmd


FROM alpine:3.21 AS runtime

RUN addgroup -S -g 1000 app \
 && adduser -S -u 1000 -G app -s /sbin/nologin app

COPY --from=builder /out/push-service /usr/local/bin/push-service

USER app

EXPOSE 8001

ENTRYPOINT ["/usr/local/bin/push-service"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-push-service" \
      org.opencontainers.image.description="SSE push notifications fed by the events.async Kafka topic."
