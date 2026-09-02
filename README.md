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
  ([ADR-0001](docs/adr-0001-fraud-service-java-flink.md)).

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
- `libraries/` — shared Python libs and the Go `kafka-client-go`.
- `infrastructure/` — Kafka, Kong gateway, Postgres, Debezium —
  [infrastructure/README.md](infrastructure/README.md).
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
- [ADR-0001: fraud service on Java/Flink](docs/adr-0001-fraud-service-java-flink.md)
- [Infrastructure](infrastructure/README.md) — Kafka, Kong, Postgres, Debezium.
