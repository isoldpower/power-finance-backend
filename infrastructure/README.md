# Infrastructure

Shared infrastructure for the CQRS workspace: the Kafka broker + topic
inventory, the Kong API gateway (custom image + in-tree plugins), the per-service
Postgres instances tuned for logical replication, and the Debezium outbox
connector.

## Kafka broker

`kafka/compose.yaml` is a single-node KRaft broker (no Zookeeper; broker +
controller in one process) in its own compose file so each service stack can
`include:` it and stay standalone-runnable, while the root compose pulls it in
transitively. Dev-only choices: replication factor and ISR collapse to 1 for the
Connect internal topics (a 1-broker cluster, else Connect refuses to start), and
`CLUSTER_ID` is a pinned 22-char base64 UUID (KRaft requires a stable id across
restarts). Production would use an odd-numbered controller quorum on separate
nodes.

> **TODO — broker is only shared within a single compose project.** Because each
> service `include:`s this file, running service stacks *separately* (e.g.
> `make antifraud up` and `make write up` in different terminals) spins up a
> *separate* `kafka` container per project on its own network — so cross-service
> flows like antifraud → `fraud.alerts` → write-service only work under the
> **root** compose (where the includes dedupe to one broker). To make the broker
> truly shared across independently-run stacks, move it onto a shared external
> Docker network (e.g. `power-finance`) that this compose owns and the services
> reference as `external`, dropping the per-service `include:` + `depends_on:
> kafka`. Deferred for now; root-compose runs are unaffected.

## Kafka topics

`kafka/topics.yml` catalogues every stream and the services on each end of it:
producers (and whether they publish directly or through a Debezium connector),
consumers with their group ids, the message key, and the settings a real cluster
should provision.

Nothing reads the file. The dev broker runs with
`KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`, so a topic is created on first
produce/consume with broker defaults and works whether or not it is listed —
which is exactly why the catalogue has to be maintained by hand, and why the
`settings` blocks describe an intended shape rather than a running one. A
production cluster would turn auto-create off and provision from this file.

The graph it records:

| Topic | Produced by | Consumed by |
| --- | --- | --- |
| `events.async` | write-service, ai-service (both via Debezium) | read-service, ai-service, webhook-service, antifraud-service, push-service |
| `notifications.inbound` | webhook-service | write-service |
| `fraud.alerts` | antifraud-service | write-service |
| `read-service.retry` | read-service | read-service |
| `read-service.dlq` | read-service | — (terminal) |
| `ai-service.retry` | ai-service | ai-service |
| `ai-service.dlq` | ai-service | — (terminal) |
| `webhooks.retry` | webhook-service | webhook-service |
| `webhooks.dlq` | webhook-service | — (terminal) |

`events.async` is the only topic with more than one producer — every service
owning an outbox routes onto it through its own connector, stamping the same
headers, so a consumer cannot tell which database a message came out of.

**Retries are per service, not shared.** `kafka-client-py` still defaults to
`events.retry`/`events.dlq`, but no service uses those defaults: read-service and
ai-service subscribe to the same event types, so a shared retry topic would hand
each of them the other's failures to reprocess — a re-dispatch that publishes a
fresh set of postings, in ai-service's case. Each service therefore publishes to
and consumes from its own pair, the way webhook-service always has.

A retry topic is consumed by the same loop that reads `events.async`, and the
loop holds a message back until its `x-retry-at` falls due: it rewinds the
partition to that message's own offset and pauses it, so every other partition
keeps moving and nothing behind it on the retry partition runs first. Sleeping
instead would stall the consumer and, past `max_poll_interval_ms`, drop it out of
its group. The DLQs stay terminal on purpose — a poison message waits there for a
human.

Kafka Connect's own `connect_configs`, `connect_offsets` and `connect_statuses`
are deliberately not catalogued: Connect creates them through its admin client
using the replication factors in `debezium/compose.yaml`, so they neither depend
on auto-create nor carry domain events.

## Kong gateway

`kong/kong.yml` is the declarative config. Kong proxies to the upstream services
by their docker-compose service names on the internal network.

### Custom image

`kong/Dockerfile` bundles `lua-resty-jwt` (not in the upstream `kong:3.7` image)
so the in-tree `clerk-jwt` plugin can `require "resty.jwt"`. The rockspec is
installed directly from GitHub (cdbattags, the current upstream maintainer)
because luarocks.org's root manifest blows past Lua 5.1's 64KB constant limit and
fails to load.

### Plugin pipeline

- **clerk-jwt** — validates Clerk session JWTs and forwards the caller's
  identity as `X-User-Id`. JWKS is cached in `gateway-redis` keyed by issuer URL;
  the single-flight fetch lock uses an nginx shared dict
  (`KONG_NGINX_HTTP_LUA_SHARED_DICT` in compose). Its priority is deliberately
  lowered so the IP-floor rate limit runs first.
- **write-ral-version** (write path) — signs the raw `X-Write-Version` from Write
  Service into the canonical `{seq}:{hmac}` form and best-effort records
  `(user_id, seq)` in redis, so later reads from the same user get a default
  Read-At-Least header. Write Service stays ignorant of HMAC and Redis.
- **read-at-least** (read path) — verifies the HMAC of inbound Read-At-Least
  headers (signed earlier by write-ral-version) and injects a default from redis
  when absent.
- **read-fallback** — transparently redirects a `507` from Read Service (its
  projection is behind the client's Read-At-Least) to Write Service's
  always-consistent fallback-read endpoints. It self-proxies in the access phase
  — the only phase that both sees the upstream status and still permits the HTTP
  call. Priority 650 keeps it below read-at-least (700) so the resolved header is
  already on the request when it forwards.

### Rate limiting (two tiers)

- **Tier 1 — IP floor** (`rate-limiting`): applies to every request (anon +
  authenticated), generous enough to survive shared egress IPs (NAT, corporate,
  mobile). Runs before clerk-jwt so attackers can't burn JWT-verification CPU by
  spraying invalid tokens — they hit the IP cap and get 429'd first. Enforced but
  invisible (`hide_client_headers: true`); the visible headers come from the
  user-tier plugin so clients see one consistent set of numbers.
- **Tier 2 — per-user ceiling** (`user-tier-rate-limit`): stricter, for
  authenticated callers; for normal traffic this is what actually bites. Read
  limits are tuned wide because read UIs are pagination-heavy. It counts on a
  SLIDING window — two buckets per window in Redis, the previous one weighted by
  the fraction of it the window still covers — so a caller cannot spend a full
  allowance either side of a boundary and get twice the limit in two seconds.
  The check and the increment run as one Redis script, so concurrent requests
  cannot both read a count below the limit and both pass, and a rejected request
  spends no budget. `Retry-After` is computed from when the estimate decays back
  under the limit, which is usually well before the next boundary.

`/api/v1/notifications/stream` (push-service SSE) has **no** rate limiting: SSE is connection-bound,
not request-bound, so a per-request counter would fire after the first event.
Concurrent-connection limits belong on Push Service itself. Its route also uses
1-hour proxy timeouts (SSE is long-lived) with nginx proxy buffering disabled
(`KONG_NGINX_PROXY_PROXY_BUFFERING=off`).

`/api/v1/chat` (ai-service WebSocket) is rate-limited the same way, which is to
say not at all, and for the same reason: a socket is one request no matter how
many messages cross it, so the per-request counters would only ever cap how
often a client reconnects. Per-message limits belong on AI Service — worth
having there once the socket does anything expensive, since an assistant turn
costs far more than a notification. Being long-lived in the same way, it gets
the same 1-hour proxy timeouts rather than the request-shaped ones the read
and write routes use.

The socket carries no token of its own. The browser WebSocket API cannot set
request headers, so a client that cannot send `Authorization` on the handshake
cannot open this route — the same constraint the SSE stream already lives with,
and the same one that would have to be solved (subprotocol or query parameter)
before a plain `new WebSocket(...)` works from a page.

There is one public surface, `/api/v1`, and the read/write split lives in the
router rather than in the paths a client types: reads and writes of the same
resource share a URL and differ only by method. `GET` goes to the Read Service,
`POST`/`PUT`/`PATCH`/`DELETE` to the Write Service.

Three kinds of route beat that bare prefix by being longer:

- the search endpoints (`/api/v1/{wallets,transactions,webhooks}/search`), which
  are reads that arrive as `POST` because a filter tree does not survive a query
  string. Their longer path outranks the write route's bare `/api/v1`, which is
  what keeps them on the read side without inventing a separate URL space for
  them;
- `/api/v1/notifications/stream`, which is routed to Push Service;
- `/api/v1/chat`, which is routed to AI Service. A WebSocket handshake arrives
  as a `GET`, so without the longer path the upgrade would be offered to Read
  Service, which does not speak it.

`/api/v1/fallback-reads/…` is internal to the `read-fallback` plugin and is
never a public path.

Global plugins: `correlation-id` (X-Correlation-ID, echoed downstream) and
`cors`.

## Write-side Postgres

`postgres/write_config/postgresql.conf` overrides the image defaults (which it
includes first) to enable logical replication for Debezium:

- `wal_level = logical` — publish all logical events to the WAL.
- `max_wal_senders = 4` / `max_replication_slots = 4` — WAL senders / replicas
  for replication headroom without flooding Debezium.
- `max_slot_wal_keep_size = '2GB'` — bounds WAL retained for an idle/stalled
  replication slot.

## AI-side Postgres

`postgres/ai_config/postgresql.conf` is the same override applied to ai-service's
own Postgres, which owns the chart of accounts and the derived entries. Its WAL
has no reader today: the settings are in place ahead of ai-service's outbox so
enabling one is a connector registration rather than a database recreation —
`wal_level` cannot be changed without a restart, and a slot cannot be created
retroactively for WAL that was never written.

## Debezium

`debezium/compose.yaml` runs the single Kafka Connect cluster
(`outbox-connect-cluster`). It lives here rather than in a service stack because
more than one service now has an outbox, and each of them `include:`s this file;
it depends on nothing but the broker, so any stack can bring it up alone.

Registering a connector, though, belongs to the service that owns the table.
Each stack contributes its own one-shot — `write-outbox-connector`,
`ai-outbox-connector` — which waits for both Connect and its own Postgres before
`PUT`ing its config. That is what keeps a single-service stack runnable: bringing
up ai-service alone never tries to register a connector against a
`postgres-write` that isn't there.

`debezium/connectors/` holds one Outbox Event Router config per outbox:

| Connector | Database | Table | Slot / publication |
| --- | --- | --- | --- |
| `outbox-connector.json` | `postgres-write` | `public.outbox_events` | `dbz_outbox_slot` / `dbz_outbox_publication` |
| `ai-outbox-connector.json` | `postgres-ai` | `public.ai_outbox_events` | `dbz_ai_outbox_slot` / `dbz_ai_outbox_publication` |

Both route to the same topic, `events.async`, keyed by `partitionkey` and
carrying the same four headers (`event_id`, `aggregate_type`, `event_type`,
`outbox_seq`), so a consumer cannot tell which database a message came out of —
which is the point. The slot, publication and `topic.prefix` must differ per
connector: a replication slot is per-database and Connect will not share one.

Each connector needs its table to exist before its task can start —
`publication.autocreate.mode: filtered` fails with "No table filters found" if
`table.include.list` matches nothing. Run the service's migrations first
(`ai-outbox-connector` waits on `ai-migrate` for exactly this reason); if a task
does fail that way, `POST /connectors/<name>/tasks/0/restart` picks it up once
the table is there.
