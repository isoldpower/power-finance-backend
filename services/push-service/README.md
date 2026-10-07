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

Only spans from real services are fanned out. A span whose `service.name` is not
listed in any node's `telemetry.serviceNames` in the infrastructure topology
(below) is dropped and counted under
`push_events_dropped_total{reason="unknown_service"}`. That covers spans from
something that reached Jaeger's OTLP port with a forged `demo-session`, a local
process with a made-up `OTEL_SERVICE_NAME`, or a span without a service name. The
allow-list is read from the embedded topology at startup, and a document without
any service names stops the service from booting. So a new service must be added
to `infrastructure_topology.json`, or its spans will never reach the demo.

`kafka.demo_spans_topic` (`KAFKA_DEMO_SPANS_TOPIC`, default `telemetry.demo-spans`)
names the topic. An empty `demo_spans_topic` in the config file turns the stream
off, and the route then answers `404`. An empty environment variable does not work
for this, because Viper ignores empty env values and falls back to the default.

## Infrastructure topology

`GET /api/v1/demo/topology` returns the static map of the system that the demo
graph is drawn on. It is public like the traces stream and served with
`Cache-Control: public, max-age=300`. The document is
`push_service/services/topology/infrastructure_topology.json`, embedded at build
time, so it ships with the code it describes. Edit it when infrastructure changes;
the package tests reject duplicate ids, unknown types and groups, dangling
connections and unconnected nodes.

```json
{
  "version": 1,
  "groups": [{"id": "write", "name": "Write side"}],
  "nodes": [{
    "id": "postgres-write", "name": "Write Postgres", "type": "database",
    "technology": "PostgreSQL 18 (logical replication)", "group": "write",
    "deployment": "core", "description": "…",
    "telemetry": {"attributes": {"db.system": "postgresql", "db.name": "power_finance_write"}}
  }],
  "connections": [{
    "from": "write-service", "to": "postgres-write",
    "kind": "query", "protocol": "sql", "description": "…"
  }]
}
```

- `type`: `client`, `gateway`, `service`, `worker`, `stream-processor`, `database`,
  `cache`, `ledger`, `search`, `topic`, `connector`, `observability`, `external`.
- `deployment`: the production VM (`core`, `search`, `stream`), or `client` /
  `external`.
- `kind`: `request`, `query`, `publish`, `consume`, `cdc`, `push`, `telemetry`. Hide
  `telemetry` (every service → Jaeger) for a cleaner graph.

`telemetry` is how a span from the traces stream finds its node:

- `serviceNames` matches the span's `service`. A node may own several (Flink's
  job and task managers), and Debezium owns none because it emits no spans.
- `attributes` matches a client span's attributes: `db.system` plus `db.name`
  for Postgres, `db.system` for Redis and Elasticsearch,
  `messaging.destination.name` for topics, `db.system: immudb` for the ledger
  (spans come from `ResilientImmudbClient`, one per client call, named after the
  method, e.g. `sqlExec`). Three Redis nodes share
  `db.system: redis`, so resolve an attribute match only among nodes connected
  to the span's own service node.
- `null` means the piece emits nothing traceable (Clerk, external APIs).
  Animate those from the connection list instead.

Python Kafka consumers create no consumer span. Their DB spans join the producer's
trace directly, so a jump from `write-service` to `read-write-consumer` should be
drawn along the `postgres-write → debezium → topic:events.async →
read-write-consumer` path from this document.

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
  - `push_events_dropped_total{reason="malformed"|"slow_client"|"unknown_service"}` — dropped events.
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
