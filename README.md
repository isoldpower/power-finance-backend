# Power Finance

> A learning-grade fintech backend built on **CQRS** — a consistency-oriented
> write side and an availability-oriented read side, bridged by a Kafka
> transactional outbox, with explicit read-your-writes, real-time SSE, signed
> webhooks, and a two-tier fraud path.

<p align="center">
  <img src="docs/images/system-design.svg" alt="Power Finance system design" width="920">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="Go" src="https://img.shields.io/badge/Go-1.26-00ADD8?logo=go&logoColor=white">
  <img alt="Kafka" src="https://img.shields.io/badge/Kafka-KRaft-231F20?logo=apachekafka&logoColor=white">
  <img alt="Postgres" src="https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white">
  <img alt="Kong" src="https://img.shields.io/badge/Kong-Gateway-003459?logo=kong&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
</p>

---

## Highlights

- **CQRS split** — a synchronous, consistency-first write side (CAP: C) and an
  eventually-consistent, availability-first read side (CAP: A), never sharing a
  database.
- **Transactional outbox → Kafka** — the write side commits domain changes and
  outbox rows atomically; Debezium ships them to `events.async` keyed per user.
- **Read-your-writes, opt-in** — clients pass a `Read-At-Least` header (a Postgres
  outbox seq); a lagging read model returns `507` and the gateway transparently
  falls back to the write side's consistent endpoints.
- **Real-time** — the push service fans `events.async` out to clients over SSE,
  authenticated per-user at the gateway.
- **Webhooks** — durable, signed (HMAC) delivery with retries, a retry topic, and
  a DLQ; schema owned by Goose migrations.
- **Immutable audit** — writes mirror to ImmuDB with SAGA compensation against
  Postgres.
- **Gateway** — Kong with in-tree Lua plugins: Clerk JWT auth, the Read-At-Least
  sign/verify pair, read-fallback, and two-tier (IP + per-user) rate limiting.
- **Fraud (planned)** — a deep-path fraud service on Java/Apache Flink
  ([ADR-0001](docs/adr-0001-fraud-service.md)).

## Services

| Service | Stack | Role |
| --- | --- | --- |
| **write-service** | Python · Django | Commands → Postgres + outbox, ImmuDB mirror, idempotency, inbound-notifications consumer |
| **read-service** | Python · Django | Projects `events.async` into Postgres + Elasticsearch read models; Redis caches; RAL |
| **push-service** | Go | SSE fan-out of `events.async`, per-user gateway auth, Prometheus metrics |
| **webhook-service** | Go | Signed webhook delivery with retry/DLQ; serves its own delivery log; owns its Postgres; Goose migrations |
| **ai-service** | Python · FastAPI | Derives the double-entry postings behind each transaction; owns its Postgres (SQLAlchemy + Alembic); assistant surface |

Shared code lives in `libraries/` (Python: `correlation-py`, `kafka-client-py`,
`read-at-least-py`, `saga-pattern-py`, `filter-grammar-py`, `webhook-catalog-py`,
`kafka-messages-proto`; Go: `kafka-client-go`). Infrastructure (Kafka, Kong, Postgres, Debezium) is in
`infrastructure/`.

## Quick start

```bash
make install            # sync the uv workspace + wire the git pre-commit hook
docker compose up -d    # gateway + all services + Kafka/Postgres/Redis
make test               # run every service + library suite
```

The gateway proxy is published on `localhost:${GATEWAY_PROXY_PORT:-8080}`. Each
service stack is also standalone-runnable from its own directory
(`docker compose up` under `services/<name>/`).

## Repository layout

- `services/` — `write-service`, `read-service` (Python/Django), `ai-service`
  (Python/FastAPI) — all uv workspace members — plus `push-service`,
  `webhook-service` (Go, `go mod`) and `antifraud-service` (Java/Flink). Each
  has its own README.
- `libraries/` — shared Python libs and the Go `kafka-client-go`. Tracing,
  context propagation and sandbox routing live in `observability-py`, which owns
  every OpenTelemetry import in the workspace; `correlation-py` is a Django-facing
  layer over it.
- `infrastructure/` — Kafka, Kong gateway, Postgres, Debezium —
  [infrastructure/README.md](infrastructure/README.md). Its `tests/contract/`
  is the cross-service contract suite: the conventions and the published
  surface, checked against `API_TARGET.md`, `API_DIFF.md` and the gateway
  config. Needs no infrastructure to run; see its
  [README](infrastructure/tests/contract/README.md).
- `docs/` — the [architecture spec](docs/architecture.md), ADRs, and diagrams.
- `old-structure/` — the pre-CQRS monolith, kept for reference only and excluded
  from all tooling.

## Make

`make help` lists targets; all assume the workspace root as the working
directory.

- **Per-service routing:** `make <service> <subcommand> [args]` is rewritten to
  `make -C services/<service>-service <subcommand>` (e.g. `make write up`,
  `make read test`, `make webhook migrate`). `make <service>` with no subcommand
  falls into that service's default goal. Router targets are `write`, `read`,
  `push`, `webhook`, `antifraud`, `ai`; root targets (`help`, `test`, `lint`, …) are only defined
  when not routing, so a service subcommand sharing a name doesn't collide. Use
  `make help`, not `make write help`, for the root.
- **Setup / quality:** `make install` (sync the uv workspace + wire the hook),
  `make test`, `make lint` / `lint-fix`, `make format` / `format-check`,
  `make typecheck`, `make precommit`.
- The git pre-commit hook is auto-installed on every Makefile invocation: every
  real target order-only-depends on `.git/hooks/pre-commit`. `VIRTUAL_ENV` is
  unexported so a stale value from a shell/hook doesn't shadow `./.venv` for `uv`.

## Docker

The root `compose.yaml` wires the Kong API gateway in front of the workspace and
`include:`s each `services/<name>/compose.yaml`, so per-service stacks stay
standalone-runnable while the root pulls them in. The shared Kafka broker
(`infrastructure/kafka/compose.yaml`) reaches the project transitively through
those includes.

Gateway specifics (plugins, rate-limit tiers, the Read-At-Least mechanism) are in
[infrastructure/README.md](infrastructure/README.md). At the compose level:

- SSE-friendly proxy defaults (buffering off, 1-hour read/send timeouts).
- `KONG_PLUGINS` enables the in-tree plugins; `CLERK_ISSUER_URL` is surfaced into
  Kong's env vault as `{vault://env/clerk-issuer-url}`.
- `READ_AT_LEAST_HMAC_SECRET` must be identical for the `read-at-least` and
  `write-ral-version` plugins so signatures produced on write responses verify on
  read requests; it is not shared with upstream services.
- `gateway-redis` backs Kong's rate-limit counters (keeping the gateway
  stateless); persistence is intentionally off — the counters are ephemeral.

## Shared dev environment

One dev host runs a single **baseline** stack; each developer gets a **sandbox**
holding only the service they are changing. The full stack is ~12–13 GB untuned on
a 16 GB box, so a stack per developer does not fit — the reasoning is in
[ADR-0002](docs/adr-0002-shared-dev-environment.md).

### Baseline

The first `baseline-up` on a fresh host builds every image (10–20 minutes); after
that it starts in under a minute. Images are local-only tags, so each service built
from source sets `pull_policy: build` — Compose would otherwise try a registry pull
first and log `pull access denied` for each one before building anyway.

```bash
make baseline-up        # pf-baseline: everything at main, tuned, Kibana off, Jaeger on
make baseline-logs
make baseline-kibana    # Kibana is scaled to 0 by default; ~768 MB when you want it
make baseline-down
```

`compose.baseline.yaml` layers over `compose.yaml`: memory limits per container,
capped ES and Kafka heaps, one Flink task slot, `OTEL_*` pointed at Jaeger, and
`SANDBOX_ID` explicitly empty, which is what makes the baseline the owner of all
untagged traffic.

### Sandboxes

**What you install locally:** `uv` and Python for the Python services, plus Go or a
JDK only if you are changing those. No Docker, no local Kafka or Postgres.

You clone the repo **on your laptop**, edit it there, and run the service you are
changing there too — the ordinary clone-edit-run loop, with your own debugger and
test runner. Only the heavy dependencies stay on the dev host: Kafka, Postgres,
Elasticsearch, Redis, ImmuDB, the gateway and every service you are *not* changing.

Reach them over SSH tunnels, so nothing on the host has to be published beyond the
gateway:

```bash
make sandbox-tunnels DEV_HOST=pf-dev-host          # leave running; Ctrl-C closes
```

Add `DEV_HOST_USER=<host account>` if your account there differs from your laptop's
— or put `User <host account>` under `Host pf-dev-host` in `~/.ssh/config` once.

Then, in another shell:

```bash
make sandbox-env NAME=$USER SERVICE=write-service DEV_HOST=localhost
set -a; . .sandbox/$USER-write-service.env; set +a
cd services/write-service
uv run uvicorn write_service.asgi:application --port 8100 --reload
```

`DEV_HOST=localhost` because the endpoints are your tunnel's near end. The generator
reads credentials from your **local** `.env`, so the passwords there must match the
dev host's — a mismatch shows up as a `500` from your service, not a connection
error, because the credentials are wrong rather than missing. See
[Environment](#environment) for the short list a laptop actually needs.

That is enough for most work — hit your own service directly, no gateway involved:

```bash
curl -H "X-User-Id: <clerk-id>" localhost:8100/api/v1/wallets
```

To exercise the **full edge** (Clerk auth, rate limits, read-fallback, read-your-writes),
let the gateway route your sandbox traffic back to your laptop. `make sandbox-tunnels`
already opened the reverse tunnel for `LOCAL_SERVICE_PORT`:

```bash
make sandbox-local NAME=$USER SERVICE=write-service TARGET=host.docker.internal:8100
curl -H "Authorization: Bearer $TOKEN" -H "X-Sandbox: $USER" http://pf-dev-host:8080/api/v1/wallets
```

Requests without `X-Sandbox` keep going to the baseline, so nobody else notices.

#### Why Kafka works over a tunnel

A Kafka client reconnects to whatever the broker *advertises*, not to the address it
dialled. The broker advertises `${KAFKA_EXTERNAL_HOST}:${KAFKA_EXTERNAL_PORT}`, so
leaving `KAFKA_EXTERNAL_HOST=localhost` is correct here: the client follows the
advertisement straight back into the tunnel. Set it to the host's name only if you
widen `BIND_ADDRESS` and connect without tunnels.

#### Running on the host instead

Some things are better off on the dev host, and `sandbox-up` runs them there with
your host-side checkout bind-mounted (`BAKED=1` to skip the mount and use the image):

```bash
make sandbox-up NAME=$USER SERVICE=write-service          # source live-mounted, ~1s reload
make sandbox-up NAME=$USER SERVICE=read-service ISOLATED=1 # own Postgres + prefixed ES indices
make sandbox-restart NAME=$USER SERVICE=read-write-consumer # workers have no reloader
```

Worth it for the compiled services (Go, Java) if you would rather not install their
toolchains, for anything that should keep running while your laptop is closed, and
for `ISOLATED=1` work. It needs the source on the host, so it is the secondary path.

```bash
make sandbox-list     # routes, per service, with TTL
make sandbox-prune    # drop routes whose container is gone
make sandbox-down NAME=$USER
```

### How isolation actually works

The sandbox id travels as a `sandbox-id` entry in the W3C `baggage` header, and
`traceparent` rides along with it, so the same mechanism gives you distributed
tracing.

Routes are keyed per service (`sandbox:route:<name>:<service>`), so one sandbox
name can override several services at once and each request is re-pointed only for
the service it addresses. Anything you have not overridden comes from the baseline.

| Hop | Carrier |
| --- | --- |
| client → gateway | `X-Sandbox` header, or `baggage` directly |
| gateway → service | `baggage` (the `sandbox-router` plugin adds the entry and overrides the upstream) |
| service → outbox row | `traceparent` / `tracestate` / `baggage` columns |
| outbox row → Kafka | headers of the same names, via the Debezium connector's field placement |
| Kafka → consumer | context re-attached; `sandbox-id` decides who owns the message |

A baseline process owns messages with **no** sandbox id; a sandbox owns only its
own. Exactly one side handles any message.

Sandbox consumers also run under their own Kafka consumer group
(`<group>-sbx-<name>`) and their own dedupe scope. Without that a sandbox joins the
baseline's group and quietly steals its partitions.

Note that a sandbox reuses the baseline's Elastic certs: `compose.sandbox.yaml`
declares the baseline's `certs` volume as external.

**Datastores are shared by default, and that has two edges.** A migration under
test would hit everyone, and so would changed *projection* logic — a sandbox
read-service writes into the real read model, and the baseline then serves those
documents. Kafka isolation does not help; the boundary stops at the datastore.

`ISOLATED=1` is the answer for both: the sandbox gets its own Postgres (one
instance, all four service databases created by
`infrastructure/postgres/sandbox_init/`), its migrations run against it, and every
Elasticsearch index is prefixed `sbx_<name>_`. `make sandbox-down` removes those
volumes. Without the flag a sandbox is only safe for changes that keep writing the
same shapes.

### Two things to know

A locally-run service exports traces through the tunnelled OTLP port, so it lands in
the host's Jaeger alongside everything else — one trace still spans your laptop and
the baseline's consumers. It reports under the **same** `OTEL_SERVICE_NAME` as the
baseline, on purpose — a sandbox is the same service, and splitting the name would
split one request's trace across two service entries. Filter on the `sandbox` field
that the log filter and baggage carry instead.

The dev secrets in `.env` (`READ_AT_LEAST_HMAC_SECRET`, `ELASTIC_PASSWORD`,
service secret keys) are shared by everyone on the host. That is acceptable for a
dev environment and must not be carried into anything real.

### Tracing

Jaeger runs alongside the baseline; the UI is on `JAEGER_UI_PORT` (16686). Tracing
stays **off** until `OTEL_EXPORTER_OTLP_ENDPOINT` is set, so running a service
straight on your laptop emits no spans and no exporter noise. Details, endpoints
and the Java agent are in
[infrastructure/README.md](infrastructure/README.md) → "Tracing".

## Environment

`docker compose` reads **one** env file by default, but the Make targets stack
several so a value can be set once and overridden where it matters.
`make env-layers` prints what will be stacked, in order; `make env-resolve`
prints the fully resolved config.

Precedence, highest first:

|   | Layer                                 | Example                             |
|---|---------------------------------------|-------------------------------------|
| 1 | shell variable                        | `WRITE_DATABASE_PASSWORD=x make up` |
| 2 | `services/<name>/.env.compose`        | per-service override                |
| 3 | `.env`                                | the workspace-wide values           |
| 4 | `${VAR:-default}` in the compose file | the dev fallback                    |

Stacked `--env-file` resolves later files over earlier ones and the shell beats
every file, so the ordering falls out of the flag order. It is unambiguous only
because every variable is prefixed by the service that owns it
(`WRITE_DATABASE_*`, `READ_DATABASE_*`, `AI_DATABASE_*`, `WEBHOOK_DATABASE_*`) —
an unprefixed variable in a service layer applies to the whole project, so
shared knobs like `LOG_LEVEL` belong in `.env`. Only files that exist are
passed: compose errors on a missing `--env-file`, so the Makefile globs rather
than listing.

**Three files, three jobs.** `.env` and `services/<name>/.env.compose` are read
by compose and reach containers. `services/<name>/.env` is read by the service
itself through `BASE_DIR / ".env"` when it runs directly on the host
(`make read run`, `uv run pytest`) and never reaches a container — no compose
file uses `env_file:`. Copy from the matching `.example`; both patterns are
gitignored, the examples are committed.

### What has to be set

Every value has a working dev fallback, so the stack starts either way. Two fail
loudly when missing and the rest fail silently, which makes the silent ones the
dangerous group:

- **Fail loudly.** `CLERK_ISSUER_URL` (Kong's `clerk-jwt` plugin fetches the
  rotating JWKS from `<issuer>/.well-known/jwks.json`; use the *production*
  Clerk instance, the dev one issues a different issuer) and
  `READ_AT_LEAST_HMAC_SECRET` (shared between the gateway's `read-at-least`
  plugin and the write side that signs `X-Write-Version` — both must hold the
  same value and rotate together).
- **Fail silently.** Four database passwords defaulting to `postgres`,
  `IMMUDB_PASSWORD` to the vendor's `immudb`, `ELASTIC_PASSWORD` and
  `KIBANA_PASSWORD` to `changeme`, and both Django `SECRET_KEY`s to
  `dev-only-secret-key-change-me`.

`docker compose config | grep -iE "changeme|dev-only-secret|PASSWORD: postgres"`
before starting anything real.

### Debezium credentials

The two connector configs under `infrastructure/debezium/connectors/` are JSON
posted to Kafka Connect's REST API, so they get no compose interpolation. They
carry `__WRITE_DATABASE_USER__` style placeholders that the
`write-outbox-connector` / `ai-outbox-connector` one-shots substitute at
registration, which is why the `WRITE_`/`AI_` values reach them and no
credential is committed. The placeholders deliberately contain no `$`: a
`${VAR}` inside a compose `command:` is interpolated by compose before the
container shell sees it, which would collapse both sides of the substitution to
the same value.

Changing a database password without that wiring is a quiet failure worth
knowing: the connector cannot connect, writes still land in the outbox table,
nothing reaches Kafka, and the read side goes stale with no error at the API.

Redis is the one store with no authentication, on any of its three instances.
That is safe only while they stay bound to loopback.

## Tooling notes

- **uv workspace** (`pyproject.toml`): `services/push-service` and
  `kafka-client-go` are Go modules, intentionally excluded — managed by `go mod`.
  `grpcio-tools` is a workspace-level dev dep so one `uv sync` makes
  `python -m grpc_tools.protoc` available for `kafka-messages-proto` codegen.
- **ruff** uses `force-exclude = true` so generated protobuf bindings are skipped
  even when a runner passes the file path explicitly — without it, ruff strips
  the side-effectful `timestamp_pb2` import from `*_pb2.py` as "unused", breaking
  descriptor-pool loading at runtime. Excludes also cover `migrations/`,
  `generated/`, `.venv`, `old-structure`.
- **mypy** excludes `fakes.py` (test-double modules at each project root share the
  top-level name `fakes`, which mypy can't map in a single run), plus
  `migrations/`, `__tests__/`, `generated/`, and `old-structure/`.
- **pre-commit** (`.pre-commit.yaml`) delegates mypy and tests to Makefile targets
  so commands have a single source of truth, and excludes `old-structure/` from
  every hook.

## Documentation

- [Architecture spec](docs/architecture.md) — components, data flows, patterns.
- [ADR-0001: fraud service on Java/Flink](docs/adr-0001-fraud-service.md)
- [ADR-0002: shared dev environment](docs/adr-0002-shared-dev-environment.md)
- [Infrastructure](infrastructure/README.md) — Kafka, Kong, Postgres, Debezium.
