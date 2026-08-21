# Infrastructure

Shared infrastructure for the CQRS workspace: the Kafka broker + topic
inventory, the Kong API gateway (custom image + in-tree plugins), the write-side
Postgres tuned for logical replication, and the Debezium outbox connector.

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

`kafka/topics.yml` is a catalogue, not a provisioning manifest. The dev broker
runs with `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`, so topics are created on first
produce/consume; a production cluster would turn auto-create off and provision
these explicitly with per-topic partition/retention settings.

- `events.async` — primary event stream. Debezium's Outbox Event Router
  publishes every write-service outbox row here, keyed by the owning user's
  external (Clerk) id for per-user ordering. Consumed by read-service
  (projections), push-service (SSE fan-out) and webhook-service (config
  projection + delivery dispatch).
- `notifications.inbound` — inbound notification requests. Other services (e.g.
  webhook-service after a delivery) produce `NotificationRequested` here; the
  write-service inbound-notifications consumer persists each one, which re-enters
  `events.async` as a `NotificationCreated` event through the outbox.
- `events.retry` / `events.dlq` — shared retry/DLQ topics for the kafka-client
  retry pipeline.
- `webhooks.retry` / `webhooks.dlq` — webhook-service's own retry/DLQ topics,
  kept separate from the shared `events.*` ones so webhook delivery backpressure
  can't interfere with the read/push projection pipelines.

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

There is one public surface, `/api/v1`, and the read/write split lives in the
router rather than in the paths a client types: reads and writes of the same
resource share a URL and differ only by method. `GET` goes to the Read Service,
`POST`/`PUT`/`PATCH`/`DELETE` to the Write Service.

Two kinds of route beat that bare prefix by being longer:

- the search endpoints (`/api/v1/{wallets,transactions,webhooks}/search`), which
  are reads that arrive as `POST` because a filter tree does not survive a query
  string, and are routed to the Read Service;
- `/api/v1/notifications/stream`, which is routed to Push Service.

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

## Debezium

`debezium/connectors/outbox-connector.json` configures the Outbox Event Router
that publishes write-service outbox rows to `events.async`.
