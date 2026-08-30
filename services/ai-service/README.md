# AI Service

FastAPI service shipping **two process types** from one codebase, per
[ADR-0002](../../.phase-5-backup/docs/adr-0002-ai-service-fastapi.md):

| Process | Entry point | What it does |
| --- | --- | --- |
| `ai-service` | `ai_service.main:app` | The assistant surface (Phase 11) and the health probes |
| `ai-dispatcher` | `python -m background_workers.main` | Consumes write-service events and derives the postings behind each transaction (Phase 5.2) |

## Layout

Four package roots, laid out the way read-service is:

| Package | What lives there |
| --- | --- |
| `service_core` | Every business decision this service makes, in vertical slices. Nothing here knows which process is running it. |
| `background_workers` | Wiring only: read the settings, build the consumer, hand each event type to a `service_core` reaction, guard it on a health probe. No logic of its own. |
| `health_probes` | The `/health/{live,ready,startup}` surface Kubernetes and Kong address, plus the checks behind it. |
| `ai_service` | Assembly only: `build_app()` and the one place routers are mounted. |

`service_core` and `health_probes` are self-contained — neither imports another
chunk, tests included. Only `background_workers` (→ `service_core`) and
`ai_service` (→ both) reach across, which is the job those two have. Where that
costs a duplicate, the duplicate is small and something asserts the copies still
agree.

Inside `service_core`:

| Slice | What it is |
| --- | --- |
| `write_reactions/` | One package per **event** — `user_created`, `transaction_created`, `transaction_updated`, `transaction_deleted`. |
| `assistant_chat/` | The chat websocket, as a slice with an `http/` edge like read-service's query slices. |
| `shared/db_connection/` | The engine, the models, `session_scope`, the settings and the Alembic chain. |
| `shared/kafka_outbox/` | The outbox mechanism: the row shape, the proto-to-row builder, the port and its SQLAlchemy adapter. |
| `shared/health_guard/` | `PostgresHealthProbe` and the connectivity errors, shared by the consumer's `HealthGuardedHandler` and by `health_probes`. |
| `shared/logging/` | The one logger hierarchy both processes write into — `registry` mints the loggers, and the three modules beside it hold the messages, one per sub-logger. |
| `shared/payloads/` | Reading a write-service event into protobuf, and turning a malformed one into the `PoisonError` that sends it to the DLQ. |

### A slice owns its whole stack

Each `write_reactions` slice is laid out the same way, one concept per file:

| Inside a slice | Holds |
| --- | --- |
| *(slice root)* | the `Effect`s themselves — what the slice exists to do |
| `contracts/` | one value type per file: the vocabulary the slice is written in |
| `repositories/` | one port per file, plus the unit of work that hands them out |
| `infrastructure/` | one SQLAlchemy adapter per file — the only modules that have heard of a database |
| `exceptions/` | one failure per file |
| `events/` | one outbox message per file, plus the function that orders a whole set of them |
| `dispatchers/` | the `PostingDispatcher` seam and its template adapter (the two dispatching slices only) |

Each slice holds exactly the types, ports and adapters that one event needs —
nothing wider. `transaction_deleted` never
learns what a `PostingLeg` is; `user_created`'s unit of work has no `entries`
property to misuse. Only `shared/` is common, and only for things no slice owns:
the connection, the outbox row, the health probe, the logger.

The cost is real and deliberate. `TemplateDispatcher`, the SQLAlchemy account
repository, the `applied_seq` guard and the stored-group-to-proto-enum map all
exist in more than one copy, and nothing but a test stops them drifting apart.
So the tests pin each copy separately: all four `events/_account_groups.py`
have their own assertion, and all three `applied_seq` guards have their own
stale-event test. A mutation to any one copy fails exactly one test — which is
the only thing standing between seven copies and a silent divergence.

The one place the copies have to agree is the chart of accounts, because
`user_created` seeds the accounts `transaction_created` later resolves. That
chart is written once as plain data in the wiring layer
(`_template_accounts.py`) and converted into each slice's types on the way in,
so a drift there is a single edit rather than three.

`write_reactions` itself holds nothing but the four slices. What they have in
common — decoding a payload, and the three sub-loggers `projection`, `dispatch`
and `accounts` that let a noisy dispatch be turned down without silencing the
projection — lives in `shared/`, because none of it knows what a slice is.

Tests sit in a `__tests__` package beside the code they cover. A double standing
in for a port belongs to the slice that owns the port;
`write_reactions/__tests__/fakes.py` holds only the protobuf message builders,
which are typed against `kafka_messages` and nothing else. The fixtures every
suite needs — a real Postgres, schema setup, per-test truncation — are in the
root `conftest.py`.

## The dispatcher

Built the same way as read-service's consumer, on the shared
[`kafka-consumer-py`](../../libraries/kafka-consumer-py) runtime: an outbox
envelope decoder, a `KafkaEventRouter`, one `ExecutionPlan` per event type made
of `SyncProcessGroup`s of `Effect`s, and every plan wrapped in a
`HealthGuardedHandler` so a Postgres outage pauses consumption instead of
burning the retry budget. Retry, DLQ and SIGTERM handling come from the same
place read-service gets them.

What differs from read-service, and why:

- **it owns its data.** Read-service projects; this service *decides*. The
  accounts and entries here cannot be re-derived from the event log, because a
  model — eventually — picks them. The transaction rows are the one projection,
  kept so a dispatch never reads another service's database;
- **no Django.** Persistence is async SQLAlchemy 2 with Alembic, so the health
  probe, the session scope and the migrations are this service's own. The engine,
  the models, `session_scope`, the settings and the Alembic chain all live in
  `service_core/shared/db_connection/` because the ASGI app reads the same
  tables, and `PostgresHealthProbe` lives in `service_core/shared/health_guard/`
  because both processes ask the same question of it — the consumer to decide
  whether to keep consuming, the endpoint to decide whether to take traffic;
- **the model sits behind a port.** `PostingDispatcher` is the seam — one per
  dispatching slice; `TemplateDispatcher` is the only adapter, and it answers
  with two legs against the accounts it was constructed with. No provider is
  contacted and no API key exists;
- **a dispatcher reads the chart of accounts, it never extends it.** A user's
  accounts are seeded when their `UserSynced` arrives; a dispatch resolves the
  ones it needs through `AccountDirectory` and posts against their ids. A
  transaction that overtakes its owner's sync raises `UnknownAccountsError` and
  retries rather than inventing a chart of accounts nobody asked for;
- **balances are recomputed, not incremented.** A dispatch replaces a
  transaction's whole leg set, so every account either set of legs touched is
  re-derived from `ai_entries` afterwards — including the ones the new legs
  walked away from. A debit raises an account in `DEBIT_NORMAL_GROUPS` (assets)
  and lowers every other; `amount` is always a positive magnitude and `debit`
  is the only place direction lives.

### What it publishes

Everything this service decides leaves through its own transactional outbox,
`ai_outbox_events` — the same shape as write-service's table, down to Debezium's
SMT column names, written in the same transaction as the state it describes.
`DispatchUnitOfWork` is what makes that free: the entries, the recomputed
balances and the rows announcing them commit together or not at all.

| Event | When |
| --- | --- |
| `AccountCreated` | an account was actually inserted while seeding a user |
| `AccountUpdated` | a balance actually moved — a recompute landing on the same number says nothing |
| `AccountPostingCreated` / `AccountPostingDeleted` | a replacement added or removed a leg |
| `AccountPostingsDispatched` | closes a replacement: how many of each, plus `balanced`, `comment` and `backend` |

A dispatch publishes its legs, then the marker that closes them, then the
balance changes. A deletion is the same shape with nothing created, and names no
backend because no dispatcher ran; a deletion that finds no legs publishes
nothing at all.

Every row is keyed by the user's external (Clerk) id, which is why
`SeedTemplateAccounts` also projects `ai_users` — `UserSynced` is the only event
carrying that id, and without it the postings would publish under `"GLOBAL"` and
push-service would refuse to deliver them. A transaction whose owner has
accounts but no projected external id raises `UnknownUserError` and retries,
which can only happen for a user seeded before that table existed.

### Subscribed events

`UserSynced` (seeds the template accounts), then `TransactionCreated`,
`TransactionUpdated` and `TransactionDeleted`. A metadata update is deliberately
not subscribed: a changed name or category does not change what the legs are
worth.

Each plan projects first and dispatches second, from the stored row rather than
from the event, so a re-dispatch reads one shape whichever event triggered it.
A dispatch replaces the whole leg set rather than diffing it — legs have no
identity outside the transaction that caused them, which makes replacement both
simpler and idempotent under redelivery.

## Health

`health_probes` serves three endpoints off the ASGI app, outside the versioned
API so a new API version cannot move them:

| Endpoint | 200 when | Who reads it |
| --- | --- | --- |
| `GET /health/live` | the worker can answer at all — nothing is checked | Kubernetes liveness; a failure restarts the pod, so it must not depend on a store |
| `GET /health/ready` | Postgres is reachable | Kong and Kubernetes readiness; a failure withdraws traffic without restarting |
| `GET /health/startup` | Postgres is reachable **and** the Alembic chain is at head | Kubernetes startup; holds the other two off during a slow boot |

Anything but `ok` answers `503` with a per-dependency reason. The body is built
by hand rather than through a `response_model`, because a model that validates
the healthy shape rejects the degraded one — which would turn an outage into a
`500` no probe knows how to read.

The two questions behind those endpoints are ports, declared at the top of
`health_probes` and implemented in `infrastructure/`:

| Port | Asks | Implementor |
| --- | --- | --- |
| `DatabaseHealth` | can the store be reached at all? | `SqlAlchemyDatabaseHealth` — `SELECT 1` |
| `DatabaseMigrations` | is the schema the one the code carries? | `AlembicDatabaseMigrations` — heads on disk minus `alembic_version` |

`pending()` answers with what the database is *missing*, never with what it has
that the code does not: a database ahead of the code is a rollback, and a probe
is not the place to have an opinion about one. It raises rather than answering
`()` when it cannot reach the database — "nothing pending" and "could not ask"
must not read the same, and a test pins that.

Both ports take an engine **factory**, not an engine. That is what keeps
`health_probes` self-contained: it reports on a database it is handed and never
imports `service_core` to find one, and because the factory arrives uncalled,
assembling the app still does not need a reachable database. The two meet in
`ai_service/build_app.py`, which is the only module that knows more than one
chunk.

Being self-contained costs three small duplications — a logger registry, the
connectivity-error tuple, and (in the tests) the chart of accounts. The chart is
the one that matters, because `user_created` seeds the accounts the dispatching
slices resolve; `background_workers` therefore carries a test asserting its chart
matches the one service_core's tests assume. That assertion lives there because
the wiring layer may import `service_core` and not the other way round.

The dispatcher exposes none of this. It has no port, and it already consults the
same `PostgresHealthProbe` in-process: `HealthGuardedHandler` pauses the consume
loop while Postgres is down rather than burning the retry budget, which is the
worker's equivalent of failing readiness.

## Environment

| Variable | Required | Meaning |
| --- | --- | --- |
| `AI_DATABASE_URL` | yes | SQLAlchemy URL, e.g. `postgresql+psycopg://postgres:postgres@localhost:5436/power_finance_ai` |
| `KAFKA_BOOTSTRAP_SERVERS` | yes | Broker list |
| `KAFKA_OUTBOX_TOPIC` | yes | Topic to consume, normally `events.async` |
| `KAFKA_AI_GROUP_ID` | yes | Consumer group id |
| `LOG_LEVEL` | no | Defaults to `INFO` |

A `.env` beside this file is read if present.

The `KAFKA_*` values are the dispatcher's alone —
`service_core.shared.db_connection.config` asks only for `AI_DATABASE_URL`, so
the ASGI app and `alembic upgrade` start without a broker address they would
never use.

## Build & Docker

The Docker build context **must** be the repository root — ai-service is a uv
workspace member depending on `kafka-consumer-py`, `kafka-client-py`,
`kafka-messages-proto` and `correlation-py` from `libraries/`. The bundled
`compose.yaml` sets `context: ../..`. To build directly:

    docker build -f services/ai-service/Dockerfile -t ai-service .

One image, three process types: the default `CMD` runs the ASGI app, and the
compose stack overrides `command:` for the dispatcher and for the one-shot
migration. The build is two-layer — workspace deps install first with the
manifests bind-mounted so they stay out of the layer, then the sources and the
editable install. The exec-form `CMD` makes the process PID 1, so docker's
`SIGTERM` reaches the dispatcher directly and its shutdown signal drains the
consume loop instead of killing it mid-batch. `PYTHONUNBUFFERED` keeps worker
logs flushing under `docker logs`.

The runtime image carries no `curl` and declares no `HEALTHCHECK`. The ASGI app
is still checked, by a compose-level healthcheck that drives `/health/live`
through the interpreter already in the image, which keeps the image free of a
tool whose only job would be to call one URL. The dispatcher has neither: a
background worker has no port, so its liveness is `restart: unless-stopped` plus
crash exit codes, as it is for read-service's consumer.

The image runs as an unprivileged `app` user; unlike read-service there is no
`user: "0"` override, because nothing here reads the elastic CA volume.

## Stack

- **ai-service** — the assistant app and the health probes, behind Kong once it
  is routed (no published host port). Reads the same tables the dispatcher
  writes. Healthchecked on `/health/live`.
- **ai-dispatcher** — the long-lived worker tailing `events.async`. No port and
  no healthcheck; a stable consumer group so offsets survive restarts and
  partitions can be shared across replicas. `stop_grace_period: 30s` gives the
  in-flight batch room to finish before `SIGKILL`.
- **ai-migrate** — a one-shot `alembic upgrade head` that both other services
  gate on with `service_completed_successfully`. Migrations are an explicit,
  idempotent step rather than something an app does on boot, so two replicas
  can't race the same DDL. It works because the image's `WORKDIR` is the
  service directory, where `alembic.ini` lives.
- **postgres-ai** — this service's *own* Postgres, holding the chart of
  accounts, the entries and the transaction projection. Loopback-only host
  publish on `127.0.0.1:5436` for tests and tooling. Compose-level interpolation
  uses `AI_DATABASE_*` so it can't collide with the write stack's
  `DATABASE_*` in a shared root `.env`; the container gets the single
  `AI_DATABASE_URL` the settings actually read, composed from those parts.

- **ai-outbox-connector** — a one-shot that registers this service's Debezium
  connector with the shared Connect cluster from
  [`infrastructure/debezium`](../../infrastructure/debezium). It waits on
  `ai-migrate`, because a connector whose table does not exist yet starts and
  then fails.

`postgres-ai` mounts `infrastructure/postgres/ai_config/postgresql.conf` and
starts with `wal_level = logical`, exactly as the write side does — that is what
the connector's replication slot needs, and it cannot be turned on without a
restart.

## Make

```
make ai migrate    # apply Alembic migrations
make ai run        # run the dispatcher
make ai serve      # run the FastAPI app
make ai test       # pytest, against AI_TEST_DATABASE_URL
make ai build-image # build the image (context = repo root)
make ai up         # start the stack (app + dispatcher + migrate + postgres-ai + kafka)
make ai down       # stop it
```

Every command-line default above is overridable on the dispatcher itself
(`--bootstrap-servers`, `--topic`, `--group-id`, `--from-beginning`), so a
replay does not need a redeploy.

## Known gaps

- **postings carry no currency.** `TransactionCreated` fields 21 and 22 held
  `currency_code` and `container_name` and went back to `reserved` when Phase 5
  was rolled back. Until they are re-added under fresh numbers, `Entry.currency_code`
  is null and a dispatcher cannot denominate a leg;
- **nobody consumes what it publishes.** The events reach `events.async`, but
  read-service does not subscribe to them yet, so its account endpoints still
  return nothing;
- **the assistant app is a stub.** `ai-service` ships in the stack, but it
  serves one echo websocket and is not routed through Kong yet, so nothing
  outside the compose network can reach it.
