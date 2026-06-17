# Webhook Service

Consumes the `events.async` Kafka topic, projects webhook configurations, and
delivers signed webhooks to subscriber endpoints with retries and a dead-letter
path. It owns its own Postgres database (delivery state + webhook configs).

## Configuration

Configuration is resolved by Viper from a YAML file, with environment variables
taking precedence over file keys.

- The config file path defaults to `./config.yaml`. Point
  `WEBHOOK_SERVICE_CONFIG_FILE` at another path to override it.
- `config-sample.yaml` is the checked-in template. Copy it to `config.yaml`
  (gitignored) for local runs.
- Environment variables override file keys: the YAML key path is uppercased with
  dots replaced by underscores (e.g. `webhook_service.port` → `WEBHOOK_SERVICE_PORT`,
  `postgres.dsn` → `POSTGRES_DSN`).
- `LOG_LEVEL` is environment-only and has no file key.

## Delivery model

The Kafka consumer never performs HTTP delivery inline. On each domain event the
dispatcher durably enqueues one `webhook_deliveries` row per subscribed endpoint
and wakes the retry scheduler; the scheduler claims due `pending` rows
(`FOR UPDATE SKIP LOCKED`) and runs every HTTP attempt. This keeps consumption
decoupled from endpoint latency, and means a delivery is sent exactly once per
terminal transition — a Kafka redelivery only re-enqueues idempotently and never
re-sends an already-succeeded or exhausted delivery.

## Database migrations

The Postgres schema is owned by [Goose](https://github.com/pressly/goose)
migrations embedded into the binary — it is no longer created at boot. Apply
them with the `migrate` subcommand:

    webhook-service migrate up        # apply all pending migrations
    webhook-service migrate status    # show migration state
    webhook-service migrate down      # roll back the last migration

`migrate` with no verb defaults to `status`. The DSN comes from the same config
as the service (`postgres.dsn` / `POSTGRES_DSN`).

Because the schema is no longer created at startup, `migrate up` must run before
the service boots. The bundled `compose.yaml` enforces this with a one-shot
`webhook-migrate` service that runs `migrate up` once Postgres is healthy; the
main service waits for it to complete successfully before starting.

## Build & Docker

The Docker build context **must** be the repository root, because the service
depends on `kafka-client-go` and `kafka-messages-proto` from `libraries/` via
local `replace` directives in `go.mod`. The bundled `compose.yaml` already sets
`context: ../..`. To build directly:

    docker build -f services/webhook-service/Dockerfile -t webhook-service .

- `GOWORK=off` keeps the image build hermetic: only the service module and the
  libraries its `go.mod` replaces are needed, not the whole `go.work` workspace.
- The image uses the exec-form `ENTRYPOINT` so the binary runs as PID 1 and
  receives docker's `SIGTERM` directly. The server's `NotifyContext(SIGINT,
  SIGTERM)` then shuts the HTTP server down gracefully and the Kafka consumer
  loop and retry scheduler drain via their cancelled context.

## Observability

The HTTP server exposes:

- `GET /healthz` — liveness.
- `GET /readyz` — readiness (`503` until the Kafka consumer is running).
- `GET /metrics` — Prometheus exposition. Alongside the default Go/process
  collectors it publishes:
  - `webhook_delivery_attempts_total` — HTTP delivery attempts.
  - `webhook_deliveries_total{outcome="success"|"retry"|"exhausted"}` — outcomes.
  - `webhook_delivery_attempt_duration_seconds` — per-attempt latency histogram.

## Delivery target safety

Webhook target URLs are user-supplied, so the sender guards against SSRF: only
`http`/`https` schemes are allowed, redirects are refused, and connections to
loopback, private, link-local and unspecified addresses are blocked at dial time
(re-checked per connection, which also defeats DNS-rebinding).

## Data autonomy

Webhook-service runs its own Postgres instance (`webhook-postgres`), separate
from the write/read service databases. It projects webhook configs from Kafka
and owns its delivery state independently.
