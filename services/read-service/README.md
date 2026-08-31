# Read Service

CQRS read side: projects the write-service event stream into denormalised
Postgres + Elasticsearch read models, serves query slices behind Kong, and keeps
Redis caches warm.

## Build & Docker

The Docker build context **must** be the repository root — read-service is a uv
workspace member depending on `kafka-client-py` and `kafka-messages-proto` from
`libraries/`. The bundled `compose.yaml` sets `context: ../..`. To build directly:

    docker build -f services/read-service/Dockerfile -t read-service .

One image, multiple process types: the default `CMD` runs the ASGI web app; the
compose stack overrides `command:` to run the Kafka consumer worker or the
one-shot index bootstrap. The exec-form entrypoint makes the process PID 1 so
docker's `SIGTERM` reaches it directly and the consumer's shutdown signal drains
the loop gracefully. `PYTHONUNBUFFERED` keeps worker logs flushing under
`docker logs`. Build is two-layer: workspace deps install first (manifests
bind-mounted so they stay out of the layer), then source + editable install.

## Stack

- **read-service** — HTTP query app, served behind Kong (no published host port,
  reachable only through the gateway).
- **read-es-init** — one-shot that creates the Elasticsearch indices + mappings
  then exits; kept distinct from consumer startup so index DDL stays an explicit,
  idempotent operation the consumer/app gate on.
- **read-write-consumer** — long-lived worker tailing `events.async`, projecting
  events and invalidating caches. No port/healthcheck (background worker);
  liveness is `restart: unless-stopped` + crash exit codes. Uses a stable
  consumer group so offsets survive restarts and partitions can be shared across
  replicas.
- **postgres-read** — a *separate* Postgres instance from the write side, holding
  only projections. Loopback-only host publish on `127.0.0.1:5434` for
  tests/tooling. Compose-level interpolation uses `READ_DATABASE_*` so it can't
  collide with the write stack's `DATABASE_*` in a shared root `.env`; the
  container env still exposes the standard `DATABASE_*` names the settings read.
- **read-redis** — read-side cache (single-wallet entries), loopback-only on
  `127.0.0.1:6381`.
- **read-migrate** — one-shot `manage.py migrate` that the app and the consumer
  both gate on, so neither starts against a schema that is behind. Mirrors
  `ai-migrate` and `webhook-migrate`; before it existed, migrations were a manual
  step and the databases silently drifted.
- **es01** — a **single** Elasticsearch node (`discovery.type=single-node`), not a
  cluster. Three nodes small enough to fit beside the rest of the stack were each
  too small for 9.x: they were OOM-killed (exit 137) on restart and the cluster
  lost quorum, which surfaces as writes timing out while cached reads still
  answer — a confusing failure to chase. One node with a real memory budget
  (`MEM_LIMIT`, 3 GiB) is steadier, and dev needs no replicas: every index here is
  a projection that can be rebuilt from `events.async`.
  The licence is `basic`, not `trial` — a self-generated trial lasts 30 days,
  cannot be restarted on the same cluster, and once expired makes security
  non-compliant, which blocks every write. `basic` is free, has no expiry, and
  still includes TLS, the native realm and RBAC, so nothing here depends on the
  difference.

The read services run as `user: "0"` only to read the elastic `setup`-minted CA
(root:root, 0750) in the shared `certs` volume; the cert mount is read-only.
Elasticsearch is reached at `es01:9200` over TLS, verified against that CA.
