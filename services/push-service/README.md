# Push Service

SSE push-notifications service. It consumes the `events.async` Kafka topic as a
groupless broadcast and fans events out to connected clients over Server-Sent
Events, authenticated per-user by the gateway.

## Observability

The service exposes three unauthenticated HTTP routes (they bypass the gateway
auth/correlation middleware):

- `GET /healthz` — liveness, always `200 ok` while the process is up.
- `GET /readyz` — readiness, `200 ready` once the Kafka consumer is running,
  `503` otherwise.
- `GET /metrics` — Prometheus exposition. Alongside the default Go/process
  collectors it publishes:
  - `push_kafka_events_received_total` — events consumed from the topic.
  - `push_events_projected_total` — events forwarded to the fanout.
  - `push_events_dropped_total{reason="malformed"|"slow_client"}` — dropped events.
  - `push_active_subscribers` — currently connected SSE subscribers (gauge).

## Configuration

Configuration is resolved by Viper from a YAML file, with environment variables
taking precedence over file keys.

- The config file path defaults to `./config.yaml`. Point `PUSH_SERVICE_CONFIG_FILE`
  at another path to override it.
- `config-sample.yaml` is the checked-in template. Copy it to `config.yaml`
  (gitignored) for local runs.
- Environment variables override file keys: the YAML key path is uppercased with
  dots replaced by underscores (e.g. `push_service.port` → `PUSH_SERVICE_PORT`,
  `log_level` → `LOG_LEVEL`).
- `log_level` sets the slog level (`debug` / `info` / `warn` / `error`, default
  `info`). It is applied before the bootstrap from the `LOG_LEVEL` env var, then
  re-applied from the resolved file+env config when `run-api` starts.
- `PUSH_SERVICE_CONFIG_FILE` is environment-only — it points at the config file
  itself, so it cannot live inside it.

## Build & Docker

The Docker build context **must** be the repository root, because the service
depends on `kafka-client-go` from `libraries/` via a local `replace` directive
in `go.mod`. The bundled `compose.yaml` already sets `context: ../..`. To build
directly:

```
docker build -f services/push-service/Dockerfile -t push-service .
```

- `GOWORK=off` keeps the image build hermetic: only the service module and the
  libraries its `go.mod` replaces are needed, not the whole `go.work` workspace.
- The image uses the exec-form `ENTRYPOINT` so the binary runs as PID 1 and
  receives docker's `SIGTERM` directly. The server's `NotifyContext(SIGINT,
  SIGTERM)` then shuts the HTTP server down gracefully and the Kafka consumer
  loop drains via its cancelled context.
