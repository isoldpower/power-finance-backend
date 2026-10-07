# Push Service

SSE push-notifications service. It consumes the `events.async` Kafka topic as a
groupless broadcast and fans events out to connected clients over Server-Sent
Events, authenticated per-user by the gateway.

## Demo traces stream

`GET /api/v1/demo/traces/stream?session=<id>` streams the spans of one portfolio
demo session (see `infrastructure/README.md` → "Tracing / Portfolio demo
sessions"). It needs no gateway auth: the route is registered as public, and Kong
fronts it with an IP rate limit instead of `clerk-jwt`. A session id that is not
16–64 of `[A-Za-z0-9_-]` gets `400`.

A second groupless broadcast consumer reads `telemetry.demo-spans` (OTLP protobuf
written by Jaeger). It reuses the same clients pool, heartbeat and SSE framing as
notifications, keyed by session id instead of user id. Each span becomes one
`event: span` frame:

```json
{"traceId":"…","spanId":"…","parentSpanId":"…","service":"write-service",
 "name":"INSERT","kind":"client","status":"ok",
 "startTimeUnixNano":"1791345070588577260","endTimeUnixNano":"…","durationMs":4.5,
 "attributes":{"db.system":"postgresql"}}
```

Only a whitelist of attributes is forwarded (`db.system`, `db.namespace`,
`messaging.system`, `messaging.destination.name`, `http.route`, the status code and
a few more, listed in `services/demotraces/contracts.go`). SQL text, URLs, Kafka
keys and user ids never leave the service. Span names are scrubbed too, because the
ASGI wrapper names its server span after the raw path (`GET /api/v1/wallets/<real id>`).
A span with `http.route` is renamed `<method> <route template>`. Any other server
span keeps only its method, or becomes `request` when it has none. Non-server span
names (`INSERT`, a topic name) pass through unchanged. Nanosecond timestamps are JSON strings
because they exceed JavaScript's safe integer range.

`kafka.demo_spans_topic` (`KAFKA_DEMO_SPANS_TOPIC`, default `telemetry.demo-spans`)
names the topic. An empty `demo_spans_topic` in the config file turns the stream
off, and the route then answers `404`. An empty environment variable does not work
for this, because Viper ignores empty env values and falls back to the default.

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
- `push_service.heartbeat_interval_seconds` (default 15) sets how often the SSE
  keepalive frame goes out. Behind a CDN this is what holds an idle stream open:
  Cloudflare cuts a connection that sends nothing for ~100s, and the Kong route
  keeps streams open for an hour, so raising this past ~60 makes streams die at
  100s with no obvious cause.

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
