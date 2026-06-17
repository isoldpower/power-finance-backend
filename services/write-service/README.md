# Write Service

CQRS write side: command handlers persist to Postgres with a transactional
outbox, mirror to ImmuDB, and Debezium ships outbox rows to Kafka. Also runs an
inbound-notifications consumer.

## Build & Docker

The Docker build context **must** be the repository root — write-service is a uv
workspace member depending on `correlation-py` (and other libs) from
`libraries/`. The bundled `compose.yaml` sets `context: ../..`. To build directly:

    docker build -f services/write-service/Dockerfile -t write-service .

Build is two-layer: workspace deps install first (manifests bind-mounted so they
stay out of the layer), then source + editable install. Runs non-root; Django
writes nothing under `/app` at runtime.

## Stack

- **write-service** — HTTP command app behind Kong (no published host port,
  `expose` documents the internal port only).
- **write-inbound-notifications-consumer** — long-lived worker tailing
  `notifications.inbound` (where e.g. webhook-service requests notifications) and
  persisting each via the `CreateNotification` command, so the resulting
  `NotificationCreated` event fans out through the outbox like any other write.
  HTTP healthcheck disabled (no HTTP); supervised by `restart: unless-stopped`.
  Stable consumer group so offsets survive restarts / replica scaling.
- **write-redis** — single logical store, currently only idempotency-key dedup
  (in-flight lock + 24h cached response). Persistence is **off**: idempotency
  state is TTL-bounded, and a Redis outage at worst means duplicate POSTs land
  during the window — caught on money endpoints by the `@idempotent` decorator
  failing closed (503) when Redis is unreachable. Kept separate from
  `gateway-redis` so rate-limit churn and idempotency state don't compete for
  memory/eviction.
- **postgres-write** — loopback-only host publish on `127.0.0.1:5433`
  (`settings.test` points here). Server config (logical replication for Debezium,
  WAL slot bounds) lives in the mounted `infrastructure/postgres/write_config/
  postgresql.conf`, which includes the image defaults then layers overrides.
- **immudb** — internal-only (`immudb:3322`), not host-published.

## Debezium outbox

The `kafka-connect` worker (Debezium) tails `postgres-write`'s WAL via logical
replication and forwards `outbox_events` rows through the Outbox Event Router SMT
onto Kafka. It is write-side-only because it knows the write schema — other
services owning an outbox would run their own Connect worker. The one-shot
`debezium-bootstrap` PUTs the connector config to Connect's REST API once it's
healthy (`PUT .../config` is idempotent, so reruns update in place).
