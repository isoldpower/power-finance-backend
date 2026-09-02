# Implementation plan for API_TARGET.md
How the surface described in [API_TARGET.md](./API_TARGET.md) is reached from what exists today,
one shippable change at a time.

Three kinds of section:
- **Phases** group steps that share a reason to be done together. Phases are ordered by dependency,
  not by value;
- **Steps** are PR-sized. Each states what changes, what it touches, and what makes it done;
- **Notes** (marked `KEEP`, `DECIDE`, or `DOC BUG`) record where the current implementation is
  already ahead of the target document, or where the document needs a decision before the step can
  be built;

Nothing in here changes the contract in API_TARGET.md. Where this plan disagrees with it, the
disagreement is written down as a `DOC BUG` or `DECIDE` note rather than silently implemented.

## Where we are today

| slice         | state                                                                                                                                           |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| Conventions   | partial — auth, RAL, rate-limit tiers, idempotency done; envelope/pagination/money/errors not                                                   |
| Accounts      | absent — no chart of accounts, no postings                                                                                                      |
| Transactions  | partial — create/update/delete/list/get/search; money flow only, no name/type/origin/category/chain                                             |
| Wallets       | partial — CRUD + list/get/search; no favorite/color/category/zero_balance/detail aggregates                                                     |
| Goals         | absent                                                                                                                                          |
| Currencies    | table + seed exist (`finances_currencies`, `digits`); no endpoints, no rates                                                                    |
| Metrics       | absent                                                                                                                                          |
| Actions       | absent                                                                                                                                          |
| Notifications | partial — model, list/get, single + batch ack, SSE at `/events`; no severity/subject/count                                                      |
| Automations   | absent                                                                                                                                          |
| Webhooks      | substantial — CRUD, subscriptions, rotation, Go delivery service with retries and HMAC signing; no event-type catalog, no delivery log endpoint |
| Assistant     | absent                                                                                                                                          |

Two structural facts shape everything below:
- Reads live at `/api/v1/reads/*` on read-service, writes at `/api/v1/*` on write-service, and the
  SSE stream at `/events` on push-service. The target has ONE flat `/api/v1` surface, so the split
  has to move into the gateway;
- Every endpoint currently returns `{data, meta}` on lists only, bare objects on single resources,
  and `{message, resource_id}` on failure with `str(exc)` interpolated into it. The envelope work is
  a rewrite of every presenter, which is why it comes first;

---

## Phase 0 — Contract foundation
**STATUS: implemented.** Both Django services, the gateway and push-service now
speak the conventions below. What was built, and where it deviates from the step
as written:

- the envelope, error taxonomy and money grammar are per-service modules
  (`data_read_core/shared/{http_contract,money}`,
  `write_service/common/{http_contract,money}`), mirroring the duplication the
  repo already uses for pagination, logging and gateway auth;
- two error codes are EXTENSIONS to the target's table: `service_unavailable`
  (503, already reachable through the RAL gate and the fallback plugin) and
  `insufficient_funds` (409, a state the domain can already be in). One detail
  code is an extension too: `invalid`, because the Detail Codes table has no
  generic "wrong shape" member;
- transaction filters gain neither `chain_id` nor `name` / `category` / `type` /
  `origin`: none of those columns exists on the read model or in the ES mapping
  yet, and whitelisting a field this service cannot answer would accept a filter
  that then fails at query time. They arrive with Phase 3;
- resource SHAPES are otherwise untouched. Phase 0 changed how amounts and
  timestamps are rendered and lifted `created_at` / `updated_at` / `deleted_at`
  out of the per-item `meta` object onto the resource, but the target's preview
  and detail field lists are each slice's own phase;
- preferences are resolved during AUTHENTICATION and bound to the caller, so a
  handler reads `request.user.preferences.currency` rather than reaching back
  into the headers. Both services wrap their user object (`GatewayUser`) instead
  of setting an attribute on it: a Django row or a domain entity loaded outside
  a request must not appear to carry request state. The wire format is unchanged
  — the gateway still forwards headers, and they are still untrusted input;
- `POST /{resource}/search` has NO fallback path. The `read-fallback` plugin
  only re-issues GETs, and the write side cannot answer a filter tree — it has
  no Elasticsearch. A search that trips the ES RAL gate therefore still returns
  507 to the client. Closing that needs a write-side search, which is not a
  Phase 0 change.

These are cross-cutting. A slice built before them has to be rewritten after them, so nothing else
starts until this phase lands. Every step here applies to the endpoints that already exist
(wallets, transactions, notifications, webhooks) and becomes the baseline for the rest.

### Step 0.1 — Response envelope and error taxonomy
**Change.** One shared HTTP-contract module per Django service: envelope builders (`ok(data, meta)`,
`fail(code, message, details)`), the `error.code` enum from Conventions → Error Codes, the
`details[].code` enum from Detail Codes, and a DRF `EXCEPTION_HANDLER` that maps domain exceptions
onto them. Replace every `except Exception: return Response({"message": f"...{error}"})` in
`query_slices/*/http/view.py` and `presentation/http/views/**`.

`meta.request_id` comes from the `X-Correlation-ID` Kong already injects; `meta.timestamp` from the
handler clock.

**Touches.** `services/read-service/data_read_core/shared/` (new `http_contract/`),
`services/write-service/data_write_core/presentation/http/`, both `settings/base.py`.

**Done when.** Every existing endpoint returns exactly `data`+`meta` or `error`+`meta`; no response
body contains an exception string; 500 responses omit `details`.

> **KEEP.** Today's handlers interpolate `str(exc)` into a 400/500 body. That is an information leak
> as much as a contract violation — this step closes both. Worth doing as one pass rather than per
> slice.

### Step 0.2 — Money shape
**Change.** Shared money module: emit as `{"amount": str, "currency": str}` at the currency's own
scale; parse request amounts leniently (zero-pad short scale) and reject `amount_malformed`,
`amount_precision`, `amount_out_of_range`. JSON numbers where an amount is expected must fail.

Scale comes from the currency table. Read-service has no currency table today — seed the same static
table there via migration rather than projecting it over Kafka.

**Touches.** new `shared/money/` in both services, every presenter, every request serializer,
read-service migration.

**Done when.** `GET /wallets` emits `"50.00"` for USD and `"90"` for JPY from the same code path, and
`POST /transactions` with `"50.005"` in USD returns 422 / `amount_precision`.

> **KEEP.** `CurrencyModel.digits` already exists with a seed migration (`0002_seed_currencies`). It
> is the target's `decimals` under another name — rename at the presentation layer only, do not
> migrate the column.

### Step 0.3 — Timestamps
**Change.** ISO-8601 with explicit offset on output; `created_at` / `updated_at` / `deleted_at`
always present, `null` when unset. Set DRF `DATETIME_FORMAT` and confirm `USE_TZ`.

**Touches.** both settings, all presenters.

**Done when.** No response contains a bare date, an epoch, or an offset-less timestamp, and
`"deleted_at" in resource` is always true.

### Step 0.4 — Keyset pagination
**Change.** Replace `StandardResultsPagination` (`LimitOffsetPagination`, default 20) in both
services with a keyset paginator:
- cursor encodes the anchor tuple, the direction, and a fingerprint of the query it was minted for
  (sort order, and for `/search` the whole filter tree);
- `limit` defaults to 25, clamps to 1..100, only a non-integer fails with 422;
- `meta` carries `limit`, `total`, `next_cursor`, `prev_cursor`, and a namespaced variant for
  embedded collections;
- `cursor_invalid` (422) and `cursor_mismatch` (422);
- Elasticsearch searches use `search_after` with the same cursor payload;
- indexes: read models are indexed on `-occurred_at` today. Add `(user_id, created_at DESC, id DESC)`
  on every paginated read model.

**Touches.** `shared/rest_framework/pagination.py` in both services, every list/search view,
read-service migration.

**Done when.** Every collection endpoint pages forwards and backwards, `offset` is gone from the API,
and a cursor sent with a changed `order` returns `cursor_mismatch`.

> **DECIDE.** `meta.total` is a COUNT per request on every page. Fine at this project's scale; if a
> collection grows past six figures the count is the expensive half of the request. The cheap fix
> later is a cached or estimated count for large collections — not worth building now, worth knowing.

> **DECIDE.** `transactions` order is `created_at DESC, chain_id ASC NULLS LAST, id DESC`. A keyset
> predicate over a nullable middle key is awkward in Postgres — every comparison needs `COALESCE` or
> a sentinel. Recommend storing a non-null sort column (`chain_sort = COALESCE(chain_id, uuid_nil)`)
> and keying on that, so the predicate stays a plain row comparison. Same problem, cheaper query
> plan. Applies again to Actions, where `severity DESC` is an enum RANK, not a string — store the
> rank as a small integer column and sort on it.

### Step 0.5 — One flat `/api/v1` surface
**Change.** Move the read/write split entirely into Kong.
- read-service routes lose the `reads` segment: `/api/v1/reads/wallets` → `/api/v1/wallets`;
- Kong routes GET to read-service and POST/PATCH/DELETE to write-service on the shared prefix, which
  the current config already does by `methods:`;
- the POST-but-read endpoints (`/api/v1/*/search`) need explicit, longer-prefix routes pointed at
  read-service so they beat the write route;
- `/events` becomes `/api/v1/notifications/stream` on push-service (also a longer-prefix route);
- `fallback-reads` stays internal to the `read-fallback` plugin and is never a public path;
- drop trailing slashes (`APPEND_SLASH = False`, paths written without them) — the target spells
  `/transactions`, not `/transactions/`.

**Touches.** `infrastructure/kong/kong.yml`, both `urls.py` trees, push-service
`presentation/http/definition.go`.

**Done when.** Every path in API_TARGET.md resolves through the gateway with no `reads` segment
visible, and `POST /api/v1/transactions/search` reaches read-service while `POST /api/v1/transactions`
reaches write-service.

### Step 0.6 — Gateway-produced responses use the envelope
**Change.** 401, 429 and any other gateway-terminated response currently return Kong's default
`{"message": ...}`. Rewrite them through the same envelope in the plugins that raise them
(`clerk-jwt`, `user-tier-rate-limit`, `rate-limiting`). Publish
`X-RateLimit-Limit-Minute`, `X-RateLimit-Remaining-Minute`, `X-RateLimit-Limit-Hour`,
`X-RateLimit-Remaining-Hour` from the per-user tier only; keep the IP tier's headers hidden
(`hide_client_headers: true` is already set on it). 429 sets `Retry-After`.

**Touches.** `infrastructure/kong/plugins/clerk-jwt/`, `.../user-tier-rate-limit/`, `kong.yml`.

**Done when.** A request with no token and a request over the limit both return the standard error
envelope with `unauthorized` / `rate_limited`.

> **KEEP.** The tier numbers in `kong.yml` already match the target's table exactly — reads
> 600/20000 per user and 1200/30000 per IP, writes 60/1000 and 200/5000. Nothing to change but the
> headers and the body.

### Step 0.7 — Idempotency contract alignment
**Change.** The mechanism exists (`write_service/common/idempotency/`: Redis atomic store, in-flight
lock, replay cache, `@idempotent(required=...)`). What is missing is its contract surface:
- map `IdempotencyKeyRequired` → 400 `idempotency_key_required`, `IdempotencyKeyReused` → 409
  `idempotency_key_reuse`, `IdempotencyInFlight` → 409 `idempotency_key_in_flight`;
- emit `meta.idempotent_replay` in the envelope on every idempotent-capable POST (the current
  `Idempotent-Replayed` header can stay as a convenience, but the contract is the meta key);
- confirm the key scope is `(user, method, path, key)` and the retention is 24 hours.

**Touches.** `write_service/common/idempotency/`, the new envelope module, `kong.yml` CORS
`exposed_headers`.

**Done when.** A replayed `POST /transactions` returns the original 201 body with
`meta.idempotent_replay: true`, and the same key with a different body returns 409.

> **KEEP.** This whole convention is already built and is one of the more finished parts of the
> system. Only the error codes and the meta key are outstanding.

### Step 0.8 — Filter policy alignment and shared registry
**Change.** The filter tree (`shared/filtering/`) already implements group nodes, leaf nodes,
operators and per-resource policies. Bring it to the target:
- add `contains` / `icontains`;
- transactions policy gains `chain_id`, `name`, `category`, `type`, `origin`; `amount` becomes a
  decimal compared numerically against the Money grammar, not a float;
- wallets policy gains `balance` and drops nothing;
- failures become 422 `validation_failed` with `filter_unknown_field`, `filter_operator_not_allowed`,
  `filter_value_type`, `filter_malformed_group`, `filter_malformed_node` (today a `FilterParseError`
  becomes a flat 400);
- move policies from `query_slices/*/policy.py` into a registry keyed by resource, because
  Automations validates `trigger.filter_body` against the same policies from a different service.

**Touches.** `data_read_core/shared/filtering/`, both search slices, later imported by Automations.

**Done when.** Every field/operator pair in Conventions → Field Policies is accepted, everything else
is rejected with the right detail code.

> **DECIDE.** `details[].field` is documented as a JSON path into the request body. For a filter
> failure that path has to point at a leaf inside a tree — fix the convention now as
> `filter_body.and[1].or[0].field_name` and use it consistently, or clients cannot highlight the
> offending condition.

### Step 0.9 — User preferences plumbing
**Change.** `currency`, `timezone` and `language` live in Clerk `unsafeMetadata` and are needed on
the request path by Metrics and by wallet `last_month`. Forward them as gateway-set headers off the
JWT claims: `clerk-jwt` already parses the full payload into `kong.ctx.shared.clerk_claims`.

Set or clear each header UNCONDITIONALLY — a `if claim then set_header end` leaves a client-supplied
header intact when the preference is unset, which lets a caller choose its own reporting currency.

Backend side: a per-request resolver that validates and falls back per field (`USD`, `UTC`, `en`).
Async workers (notifications, assistant, automations, webhooks) read Clerk directly instead.

**Touches.** `infrastructure/kong/plugins/clerk-jwt/handler.lua`, new `shared/preferences/` in
read-service.

**Done when.** A forged `X-User-Currency` cannot influence a response, and an unset preference
produces the documented default.

> **DECIDE.** Any cache key for a Metrics response MUST include the resolved reporting currency.
> Otherwise a user who switches currency gets a `meta.cached: true` payload denominated in the old
> one, and the doc explicitly says nothing invalidates on the server.

---

## Phase 1 — Currencies
**STATUS: implemented.** All four steps landed on the read side. What was built,
and where it deviates from the step as written:

- the reference table gained a `symbol` column (migration `0008_currency_symbol`,
  backfilled for the 34 seeded codes). It is READ-SIDE ONLY: nothing in the write
  domain formats money for a screen, so the write-side `Currency` value object is
  untouched and the two seed lists no longer match field-for-field;
- `CurrencyScales` widened into `CurrencyCatalog` (`shared/money/currency_catalog.py`)
  because the same one-read-per-process table now answers `name` and `symbol` as
  well as `digits`. `decimals_for` / `decimals_or_default` behave exactly as
  before; `table()` was replaced by `supports()` at its one call site;
- the rate provider is `open.er-api.com` — free, no key, no attribution clause,
  ~160 codes. It publishes ONCE A DAY, which is why the freshness rule is two
  settings rather than one: `TTL_SECONDS` (900) says how often we ask, and
  `MAX_AGE_SECONDS` (172800) says how old the FEED's own timestamp may be before
  we refuse to serve it. A Redis TTL alone cannot express the second — a stalled
  feed keeps answering, and only its own timestamp gives it away;
- a second provider, `StaticRateProvider`, serves fixed made-up numbers and talks
  to nothing. Test settings select it so the endpoints are exercisable without a
  network round trip; selecting it logs a warning, because a deployment that
  reaches for it by accident should be noisy;
- `GET /currencies` is NOT cached in Redis. The catalog already holds the table in
  process memory, so a Redis hop would be the slower path. It reports no
  `meta.cached` at all rather than a permanent `false`;
- the rates path parameter is `{code}`, not the target's `{currency-code}`: a
  Django path converter cannot carry a hyphen. Client-visible URLs are identical;
- `?target=` accepts both `target=RUB&target=EUR` and `target=RUB,EUR`, since the
  target document writes the param as a list without fixing an encoding. An
  unknown code in it is a 422 rather than a silent omission from the map — a
  missing entry would otherwise be indistinguishable from `rate_unavailable`;
- none of the three endpoints applies the Read-At-Least gate. Reference data and
  a shared rate feed carry no user write version, so there is nothing to be
  behind.

Small, self-contained, and unblocks money scale enforcement plus every conversion downstream.

### Step 1.1 — `GET /currencies`
Non-paginated: `limit: null`, both cursors `null`, always complete. Served from the seeded table
projected into read-service in Step 0.2. `digits` presents as `decimals`.

### Step 1.2 — Rate provider
Upstream rate source behind an interface, cached in Redis with the fetch timestamp. Unknown code →
422 `unsupported_currency`; known code with no fresh rate → 409 `rate_unavailable`. This is the first
step with a third-party dependency: pick the provider, cache aggressively, and treat staleness as a
409 rather than serving an old number silently.

### Step 1.3 — `GET /currencies/rates/{currency-code}`
`base` + `rates` map of unpadded decimal strings, `target` filter echoed in `meta`, `fetched_at` in
`meta`.

### Step 1.4 — `GET /currencies/convert`
`from` / `to` money objects plus a non-money `rate` string with up to 12 fraction digits. `amount` is
validated against `from_code`'s scale. The server does the rounding once; the client renders `to`.

---

## Phase 2 — Wallets to target shape
**STATUS: implemented.** (`recent` on wallet detail was deferred to Phase 3 and landed there.)
Wallets are the most-used resource and the cheapest large win after Phase 0.

Both `DECIDE` blocks below were answered, and the answers turned out to be the
same answer:

- **`zero_balance` is the wallet's DATUM, not a floor.** It is the point at which
  the wallet holds nothing of the user's own money — a credit line. The balance
  may go below it; below it the user OWES `zero_balance - balance`. What the user
  owns is `balance - zero_balance`. A fresh credit card with a 100 limit opens at
  balance 100 and owns 0; spend 30 and it owns -30. A cash wallet has a datum of
  0 and owns its whole balance;
- **DELETE closes only when `balance == zero_balance`** — settled in both
  directions, since money left in the wallet and debt still owed on it are both
  unfinished business. `WalletAggregate.is_empty` is that comparison, and the
  guard sits after the already-closed check so a repeat DELETE still answers 200;
- **net worth (Phase 6) sums `balance - zero_balance`**, and Phase 5 models the
  drawn portion of a credit line as a liability. Nothing in Phase 2 computes it —
  the point of settling it now was to make sure Phase 2 stored the right thing.
  `WalletAggregate.owned` exists and is the figure those phases will fold;
- **`opening_balance` reaches the ledger as a real transaction**, not as a
  column. `POST /wallets` emits `WalletCreated` and, when the opening amount is
  non-zero, a `TransactionCreated` alongside it in the same outbox emission. Both
  balance derivations then need no special case at all — the write side folds it
  as an unsettled transaction, the read side accumulates it from 0 — and Phase 5
  adds the equity counter-posting with no migration and no backfill. The
  "temporary inconsistency" the step warned about never gets created.

Consistency check that ties the two together: a wallet is closeable exactly when
it contributes zero to net worth.

Other deviations from the steps as written:

- **`opening_balance` defaults to `zero_balance`, not to zero.** Not a separate
  decision so much as the only default consistent with the datum rule: a wallet
  nobody funded should open OWNING and OWING nothing, and for a credit line that
  means opening at its limit. For an ordinary wallet the datum is 0, so the two
  defaults agree. Overrule this if a fresh credit card should instead open
  already in debt for its full limit;
- `opening_balance` is never stored and never echoed — the target's POST response
  does not contain it either. Its opening transaction DOES show up in
  `GET /transactions`, with nothing but a timestamp to tell it apart until
  Phase 3 gives transactions a `name` and an `origin`;
- `WalletCreated` / `WalletUpdated` carry the FULL post-update state in the new
  fields rather than a diff. PATCH is partial, so a diff would need a presence
  flag per field; an overwrite of the whole mutable set is smaller and
  idempotent. `previous_title` / `new_title` stay as they were;
- **the read projection no longer hard-deletes a closed wallet** — it stamps
  `deleted_at` on the row and on the ES document. The target says a closed wallet
  "continues its existence" and DELETE returns a body carrying `deleted_at`,
  neither of which survives dropping the row. Lists and search filter it out;
  `GET /wallets/{id}` still resolves it. `WalletReadModel` gained `deleted_at`
  and the list index gained a partial-index condition on it;
- `PATCH` renamed its field from `new_name` to the target's `name`. A client
  still sending `new_name` now changes nothing instead of failing, since every
  PATCH field is optional;
- `PUT /wallets/{id}` is not in the target but exists, so it grew the same
  fields. It keeps REPLACE semantics — an omitted field resets to its default —
  against PATCH's leave-alone semantics;
- `color` is validated as `#RGB` / `#RRGGBB` / `#RRGGBBAA`. The target shows
  `#FF0000` but names no format;
- `zero_balance` stores at `decimal_places=2` on both sides, matching the
  existing `balance` column. That is wrong for JPY (0 digits) and BHD (3) — a
  pre-existing debt of the balance column, now shared by one more field, not a
  new one;
- **the window became a query param, and the response key followed.** The target
  hardcodes `last_month` and gives wallet detail no way to ask for another range,
  which pushes any other window onto `POST /transactions/search` plus client-side
  aggregation. `?period=last_week|last_month|last_year|all_time` (default
  `last_month`) selects it, the response key is `period`, and `meta.period`
  echoes the choice. Keeping the key `last_month` while the window is the
  client's would have made the field lie. Recorded in API_DIFF.md;
- every window except `all_time` is a CALENDAR window resolved in the caller's
  timezone, and all of them are half-open so consecutive windows tile without
  double-counting the boundary. `all_time` returns `(None, None)` and the bounds
  are dropped from the query rather than widened to an arbitrary epoch. Both
  services share the same `Period` enum and `period_bounds` helper;
- **`period` is computed on every request and never cached**, like `recent`. The
  window is chosen by the caller and resolved in their timezone, so it does not
  belong under a cache key that identifies only the wallet. `meta.cached`
  continues to report on the wallet body;
- an unknown `period` is 422 `validation_failed` rather than a silent default —
  consistent with how an invalid cursor is handled, and unlike the PREFERENCE
  headers, which degrade quietly because the client did not ask for them;
- the write side's fallback-read wallet detail computes `last_month` too, by
  folding a windowed ImmuDB query in Python. The reroute is internal and must
  never be visible to a client, so the two shapes have to match field for field;
- the wallet filter policy needed no change: `name`, `currency`, `balance`,
  `created_at` already matched Step 2.5 exactly.

### Step 2.1 — Domain and storage fields
Add `category` (free-form string), `color`, `favorite`, `zero_balance`, and `opening_balance` to the
wallet aggregate, the write ORM, the outbox event payload (proto), and the read projection.
`title` presents as `name`.

**Touches.** `data_write_core/domain/entities/wallet.py`, `infrastructure/orm/wallet.py`, a write
migration, `libraries/kafka-messages-proto/`, `data_read_core/shared/postgres_orm/wallet.py` + read
migration, `write_reactions/wallet_reactions/`.

> **DECIDED (2026-08-21).** `opening_balance` does not create money from nothing: it is emitted as a
> real opening transaction, so the ledger is consistent from the first request and Phase 5 only adds
> the equity counter-posting.

> **DECIDED (2026-08-21).** `zero_balance` is a credit datum, not an alert floor and not a
> constraint. See the STATUS block above.

### Step 2.2 — Preview shape and ordering
Presenter emits the target preview object. Ordering becomes `favorite DESC, created_at DESC, id DESC`
with a matching index, applied AFTER filtering.

### Step 2.3 — Mutation semantics
`POST` (idempotency optional), `PATCH` (name, favorite, category, zero_balance, color), `DELETE` as
soft close returning 200 with the same body on repeat, and 409 `wallet_not_empty` when the balance is
non-zero. Closed wallets leave lists and search.

### Step 2.4 — `GET /wallets/{wallet-id}` detail
Adds `last_month.inflow` / `last_month.outflow` (calendar month in the user's `timezone` preference,
from Step 0.9, in the WALLET's currency — nothing converted) and the `recent` embedded collection
paginated through the endpoint's `limit`/`cursor` with `meta.recent`.

**Both landed — `last_month` in Phase 2, `recent` in Phase 3.** `recent` waited because its items are
transaction previews carrying `name`, `type`, `origin`, `category` and `chain_id`, every one a Step
3.1 field; shipping it earlier would have published a preview shape that changed one phase later. It
now embeds the SAME preview object `GET /transactions` returns, in the same
`created_at DESC, chain_id ASC NULLS LAST, id DESC` order, paginated through the endpoint's
`limit`/`cursor` under `meta.recent`, and excluding cancelled transactions.

### Step 2.5 — `POST /wallets/search`
Policy fields `name`, `currency`, `balance`, `created_at`. Favorites lead the matching results and
never bypass the filter.

---

## Phase 3 — Transactions to target shape
**STATUS: implemented, all eight steps including chains.**
The largest single phase. Split it exactly as listed; do not attempt chains before 3.1–3.6 land.

The split in Step 3.1 came out DIFFERENT from — and better than — the step as
written, on a suggestion made while scoping it. The step proposed keeping the
ledger row as "the transaction" and hanging a mutable metadata row off it. The
objection was exact: a ledger row is immutable, so `name`, `category` and
`evidence` cannot live on it, and bolting them on through `adjusts_other` would
mean a rename appends a row to an append-only MONEY ledger. What landed instead:

- **a Transaction is a new aggregate** in the write Postgres, holding `name`,
  `category`, `evidence_url`, `origin`, `chain_id` and `deleted_at`. It owns one
  or more immutable **money flows** in ImmuDB. Creating appends one flow;
  adjusting appends a delta linked by `adjusts_other`; cancelling appends an
  inverse linked by `cancels_other`. Nothing ever rewrites a flow;
- the old `TransactionEntity` became `MoneyFlowEntity`, and everything around it
  followed: `MoneyFlowData`, `MoneyFlowMapper`, `MoneyFlowRepository`,
  `ImmudbMoneyFlowRepository`, `ImmudbMoneyFlowStep`. `TransactionRepository` is
  now the Postgres one. The rename touched ~160 references and is why the API's
  word "transaction" and the code's word finally mean the same thing;
- **`type` is not stored anywhere.** It is read off the sign of the folded flows:
  negative is an expense, positive an income. `money.amount` goes out as a
  positive magnitude and the direction rides in `type`, so the two cannot
  contradict each other and an impossible state is unrepresentable. An
  adjustment that would cross zero is refused with
  `TransactionDirectionChangeError` — that is a different operation, not an edit;
- **`amount` excludes cancelling flows.** A cancelled transaction still reports
  the figure it was FOR, which is what DELETE echoes back and what detail shows
  beside `deleted_at`. `ledger_effect` sums every flow and is what the wallet
  balance follows — it nets to zero once cancelled. Two different questions, two
  properties;
- `collapse_ledger` and its `CollapsedTransaction` were DELETED. Folding the
  ledger into user-facing transactions was exactly what the split made
  structural: flows carry `transaction_id`, so the fold is a group-by, and
  `TransactionAggregate.amount` is the whole of it;
- **the opening balance from Phase 2 is now a real transaction**, named
  "Opening balance", not an anonymous ledger row. The API_DIFF note about it
  having "nothing but a timestamp to tell it apart" is resolved.

Deviations from the remaining steps:

- **`PATCH` no longer accepts `new_amount`; corrections moved to
  `POST /transactions/{id}/adjust`.** The target reassigns PATCH to metadata and
  defers adjustment transactions, so it names no path for restating an amount —
  but correcting a figure has to remain possible without destroying the record,
  and cancel-and-recreate would lose both the audit trail and every reference to
  the id. The endpoint takes the new TOTAL as a positive magnitude, signs it with
  the transaction's existing `type` (so a correction can never flip an expense
  into an income), and appends the DIFFERENCE as an adjusting flow. Absolute
  rather than incremental, so a retry cannot double-count. Ahead of the target
  and recorded in API_DIFF.md; the path may be renamed when the spec chooses one;
- **the read projection soft-cancels a transaction** instead of dropping the
  row, matching what Phase 2 did for wallets and for the same reason: DELETE
  returns a body carrying `deleted_at`, which does not survive dropping the row.
  The reaction is idempotent — a redelivered `TransactionDeleted` must not
  reverse the balance twice;
- **Step 3.8's nullable `chain_id` keyset** is solved with a sentinel column.
  `chain_sort` holds `chain_id` or the largest possible UUID, so
  `chain_id ASC NULLS LAST` becomes a plain comparable value a cursor can carry.
  That answers the Step 0.4 open decision for this ordering. The DTOs carry
  `chain_sort` without presenting it, because the cursor is minted from the DTO;
- **`wallet.name` is denormalised onto the transaction row.** The cost is a
  reaction (`RenameWalletInTransactions`) that carries a wallet rename into every
  transaction of that wallet — which is the trade the step asked for;
- `TransactionMetadataUpdated` is a NEW event, separate from `TransactionUpdated`.
  One is a rename, the other is money; a subscriber almost never wants both;
- **chain pagination follows the target literally** (`meta.transactions` with a
  cursor), per an explicit decision. Both cursors are always null because a chain
  holds at most 100 entries and every one is in the response. API_DIFF.md records
  that nothing consumes a chain cursor;
- `GET /transactions/{id}` returns `postings: []` and `analysis: null` rather
  than omitting them, so a client does not have to branch on the keys existing.
  Both are filled by Phase 5;
- transaction cache keys gained a schema segment (`read:transaction:s2:{id}`),
  as the wallet ones did in Phase 2 — the cached DTO changed shape and stale
  entries would otherwise reach a constructor that no longer accepts them.

### Step 3.1 — Split the immutable flow from the mutable metadata
A transaction today is `(source_wallet_id, amount, cancels_other, adjusts_other)` in ImmuDB. The
target adds `name`, `type`, `origin`, `category`, `evidence` and `chain_id`, and `PATCH` mutates
three of them.

**Change.** Keep the money flow in ImmuDB (append-only, auditable — see the note below) and put the
mutable metadata in the write Postgres keyed by transaction id. `type` and `origin` are immutable and
belong with the flow; `name`, `category` and `evidence` are mutable and belong in Postgres. The
projection joins them.

**Touches.** `infrastructure/immudb/database_schema.py`, a new write ORM model, the transaction
mapper and repository, the outbox payload, the read projection.

> **KEEP.** The ImmuDB ledger is a stronger audit story than the target document assumes — it never
> contemplates where a transaction lives. Do not weaken it into a mutable row to make `PATCH` easier.
> This split is exactly why `PATCH` is documented as never touching money.

> **KEEP.** `occurred_at` exists on the read model and has no counterpart in the target, which orders
> and reports on `created_at` alone. A user-stated transaction date is genuinely more correct for a
> finance product than the row's insert time. Keep the column, order on `created_at` for v1
> compliance, and expose `occurred_at` later as an additive field.

### Step 3.2 — Preview shape
`money`, `type`, `origin`, `category`, `chain_id`, and an embedded `wallet: {id, name}`. The wallet
name has to be denormalised into the transaction read model (or joined) — denormalise, and update it
from the wallet-updated reaction.

### Step 3.3 — `POST /transactions`
Required `Idempotency-Key` (already enforced), flat `amount` + `currency` request pair, 409
`wallet_closed` against a soft-deleted wallet, `type`/`origin` validation.

### Step 3.4 — `PATCH /transactions/{id}`
`name`, `category`, `evidence` only. Returns the preview shape — no `evidence`, `postings` or
`analysis` in the response even when `evidence` was just set.

### Step 3.5 — `DELETE /transactions/{id}`
Soft cancel, idempotent, 200 with the same body on repeat, excluded from lists and search.

### Step 3.6 — `POST /transactions/search`
Extend the ES mapping with `name`, `category`, `type`, `origin`, `chain_id`; add a reindex to the
existing `init_elasticsearch_indices` command path. Cancelled transactions excluded.

### Step 3.7 — Chains
`POST /transactions/chains`: chain aggregate, `temporary_id` / `after` DAG with 422 `chain_cycle`,
`chain_unknown_reference` and `chain_too_long` (>100), all-or-nothing across ImmuDB and Postgres
through the existing SAGA steps, one idempotency key covering the whole chain, and
`details[].field` pointing at the failing entry by index. Then
`DELETE /transactions/chains/{chain-id}`, idempotent.

> **DECIDED (2026-08-21): implement the cursor as documented.** The chain response carries the
> `meta.transactions` triple the target specifies. Both cursors are always null in practice — every
> leg is in the response — so the triple is shape compliance, not a paging mechanism. Nothing
> consumes a chain cursor; `POST /transactions/search` on `chain_id` remains the way to re-read a
> chain. Recorded in API_DIFF.md so clients do not go looking for a cursor to follow.

### Step 3.8 — Ordering
`created_at DESC, chain_id ASC NULLS LAST, id DESC` via the sentinel sort column from Step 0.4, with
a matching index.

---

## Phase 4 — Goals
**STATUS: implemented, all three steps.**
Depends on chains (Phase 3.7): funding and draining a goal is a transfer, and `DELETE` refuses a
non-zero `progress`.

Step 4.2's money container landed as an **exclusive arc** and was then converted to a **shared
supertype table** (migration `0010_money_container_base`), which is where it now stands.

- `MoneyContainerModel` (`finances_money_containers`) holds everything a wallet and a goal have in
  common — id, `kind`, name, currency, owner, timestamps — and `WalletModel` and `GoalModel` are
  multi-table children of it, each keeping only what is peculiar to its kind. Both child tables kept
  their existing `id` column; it is now a foreign key into the parent rather than a bare uuid, so
  the conversion moved columns without touching a primary key;
- `TransactionModel` carries one mandatory `container` foreign key. The arc it replaced — two
  nullable foreign keys under a `ft_exactly_one_container` check constraint — could not be violated
  either, but it could only be read by asking which side was null, and it grew a column per kind.
  The kind now lives on the container, which is the thing it describes, and is read across the key
  rather than copied alongside it;
- the ledger and the metadata are now the same id space by construction. ImmuDB records flows
  against a container id and Postgres records a transaction against a container id; before, the
  Postgres side held two columns whose union happened to be that space;
- `DjangoMoneyContainerRepository` became one query. Resolving an id used to mean probing the wallet
  table and then the goal table, hoping one owned it, with the miss costing two round trips;
- above the repository nothing branches. `MoneyContainerRef` (id, kind, currency, title, is_closed)
  is what commands pass around, `MoneyContainerAggregate` is the protocol both `WalletAggregate` and
  `GoalAggregate` satisfy, and `DjangoMoneyContainerRepository.resolve` is the single place that
  knows an id might name a goal. `LoadContainerMixin` replaced `LoadWalletMixin` on the whole
  transaction path; `LoadedWallets` became `LoadedContainers` and the old module is gone;
- `TransactionEntity.wallet_id` became `container_id` + `container_kind`, and the same rename went
  through the transaction domain events. A field named `wallet_id` that may hold a goal id is
  exactly the lie this step existed to prevent;
- the ImmuDB ledger KEPT its column names. `transactions.source_wallet_id` and
  `balance_checkpoints.wallet_id` hold container ids now. Renaming a column in an append-only store
  forks its history for a cosmetic gain — every row written before the rename would still carry the
  old name. The mapper bridges `container_id` ↔ `source_wallet_id`;
- the read side has no foreign keys, so it took an explicit `container_kind` column instead. That
  column is load-bearing in two queries: goal history and the goal-rename denormaliser both filter
  on it, because `wallet_id` holds an id of either kind.

> **COST OF THE CHANGE.** Every wallet and goal read is now a join, and a wallet list ordered by
> `favorite` then `created_at` sorts across two tables, so that ordering can no longer be served by
> one index. A third container kind is now a table plus a `kind` value rather than a column on
> `finances_transactions` and a branch in the resolver, which is what the change bought.
>
> `0010` is written with `SeparateDatabaseAndState` and is reversible in both directions with data
> intact — the rollback re-splits the single key back into the arc using the kind on the container
> row, which is only possible while all three columns exist. Do not reorder its operations.

Other notes from the build:

- goal `history` entries are derived from the goal's transactions, one entry each, not from Phase 5
  postings. A goal's history is a record of money moving in and out of it, which is knowable
  deterministically; waiting for the dispatcher would have made the collection empty for no reason.
  Entries carry an `id` — the target's examples omit one, which cannot work for a keyset cursor;
- `GoalClosedError` maps to 409 `wallet_closed`, deliberately NOT a new code. The target defines that
  code as "target wallet is soft-deleted", and from the client's side a goal IS the target it named
  in `wallet_id`. A separate `goal_closed` would make callers branch on a distinction the request
  never drew;
- `TransactionCreated` gained `currency_code` and `container_name` (fields 21 and 22). Phase 5's
  dispatcher has no access to anyone else's database and could not otherwise denominate a posting at
  all. It also removes the read projection's ordering dependency on the wallet row existing first.

### Step 4.1 — Goal aggregate and storage
`name`, `currency` (fixed at creation), `target`, `finish_at`, `url` (always `null` for now), the
three structural timestamps. Write ORM, events, read projection.

### Step 4.2 — Money containers
Anywhere the API accepts a `wallet_id`, a goal id is accepted too.

**Change.** Introduce one internal money-container reference rather than branching on "wallet or
goal" at every call site. Transactions point at a container; wallets and goals are two kinds of
container. Doing this at 4.2 is cheap; doing it after Metrics and Automations reference wallet ids
is not.

### Step 4.3 — Endpoints
`GET /goals` (ordered `created_at DESC, id DESC` — not by `finish_at`), `POST`, `GET /{id}` with the
`history` embedded collection, `PATCH` (`progress` ignored if sent), `DELETE` with 409
`goal_not_empty`.

No `/search` endpoint. That is a decision in the target, not an omission — do not add one by symmetry.

---

## Phase 5 — Accounts and postings
The first slice with a real AI dependency, and the one Metrics is built on. Everything before this
point is deterministic.

**STATUS: implemented, all four steps.** The slice was rolled back once and rebuilt by hand;
`.phase-5-backup/` still holds the discarded first pass. Both conclusions that rollback was for
survived into what shipped:

- **ai-service OWNS accounts and postings.** `ai_accounts` and `ai_entries` live in its own
  Postgres behind async SQLAlchemy and Alembic, so deciding an account and writing a posting is one
  local transaction rather than a blind emit into a projection the producer cannot read;
- **the producer has a transactional outbox**, so a publish failure after commit cannot lose a
  posting from the read side.

What the build settled beyond the steps as written:

- **the dispatcher is deterministic, and that is the seam, not the slice.** `TemplateDispatcher`
  emits one leg per template account behind a `PostingDispatcher` port with a
  `DispatcherFactory` in front of it. The "real AI dependency" this phase was named for is the one
  thing still to swap in, and swapping it changes no consumer, no event and no endpoint;
- **accounts are denominated in a single BOOK currency** (`BOOK_CURRENCY`, `USD`). A posting is
  converted into it before it is summed, which is why an entry carries both its own `amount` and a
  `book_amount` + `conversion_rate`, and why the account's balance is one currency rather than a
  mixture. `AccountCreated` (field 107) and `AccountUpdated` (field 108) carry `currency_code`, and
  `AccountUpdated` RESTATES it so a consumer that missed the creation still learns it;
- **`meta.groups` honours `lowbar` but not `group`.** The target only says it ignores the group
  filter. Ignoring the threshold too would make a tab advertise a count that selecting it does not
  produce;
- **`lowbar` compares MAGNITUDES.** A liability's balance is negative, so a signed comparison would
  empty that group the instant any client set a threshold. The parameter exists to hide trivial
  accounts, and triviality has no sign;
- **the threshold is converted, not the balances.** `lowbar` arrives in the caller's currency and
  balances are held in the book currency; converting the threshold once per book currency in play
  keeps the comparison something an index can serve, where converting every balance would not. A
  `lowbar` of zero — the default — skips the rate lookup entirely;
- **`GET /accounts/{account-id}` replaced `GET /accounts/{account-id}/postings`.** The postings
  collection was a stand-in for the detail endpoint the target actually specifies, not an addition
  to it, so it went when the detail arrived. History is read live and only the account ROW is
  cached, exactly as goal detail does it;
- both `DOC BUG` notes below were resolved the way they recommend: history entries carry an `id`,
  and the account shape carries `created_at` / `updated_at`.

### Step 5.1 — Chart of accounts and entries
Account model (`group` ∈ assets/liabilities/equity, `name`, derived balance) and an entry/posting
model (`title`, `debit`, `icon`, `money`, `source_transaction`, `created_at`).

> **DOC BUG.** Posting and history entries carry no `id` in any example, but they are paginated
> collections and keyset pagination needs a stable anchor. Give entries an `id` and add it to the
> shape — it is an additive change and the alternative is no cursor.

> **DOC BUG.** `GET /accounts` orders `created_at DESC, id DESC`, but the account object in the
> example has no timestamps at all. Either add the three structural timestamps to the account shape
> (consistent with every other resource) or state that the sort key is not exposed.

### Step 5.2 — Dispatcher
A worker consuming `transaction.created` that derives the double-entry legs, writes the entries,
recomputes account balances and emits the projection event. `analysis.balanced` and its `comment`
are computed here — most commonly `false` when the two legs land in different currencies. It is a
diagnostic, never an error.

### Step 5.3 — Endpoints
`GET /accounts` with `group`, `lowbar` + `currency`, both echoed in `meta`, plus `meta.groups` counts
that ignore the `group` filter (a second, cheap aggregate query). `GET /accounts/{account-id}` with
the `history` embedded collection.

Ordered `created_at DESC, id DESC` like every other collection — `group` filters and does not order.
`ACCOUNT_CHART`, the group-then-name sort the first cut used, was deleted rather than left unused.

### Step 5.4 — Transaction detail gains `postings` and `analysis`
Closes out Step 3.1's deferred half of `GET /transactions/{id}`.

---

## Phase 6 — Metrics
Depends on Accounts (5) for the balance sheet, Currencies (1) for conversion, and preferences (0.9)
for the reporting currency.

**STATUS: implemented, all three steps — on ONE endpoint.** What the build settled beyond the
steps as written:

- **the target's three paths are one `GET /metrics` with boolean selectors** (`balance`,
  `net-worth`, `cash-flow`, each defaulting to true). The sections read the same rows and differ
  only in the fold, so three paths meant three round trips, three authentications, three cache
  entries and three scans of `read_transactions` to fill one screen. Merged, net worth's opening
  balance, its all-time total and cash flow's two directional figures are conditional aggregates in
  a SINGLE grouped query, one `MoneyFolder` resolves each rate once for the whole response, and one
  cache entry covers it. A section not asked for costs none of its queries; a section not returned
  is `null` rather than absent, so the three keys are always there. The trade is that fetching one
  section alone now costs two explicit `false` params — the uncommon call paying for the common
  one. Recorded in API_DIFF.md;
- **net worth is read off TRANSACTIONS, not off the ledger.** It is the running total of every
  non-cancelled transaction against one of the user's containers. A transfer nets to zero across
  its two legs on its own and an opening balance is a real transaction, so nothing has to be
  special-cased — and the figure is correct before ai-service has dispatched anything, which it
  would not be if net worth were derived from accounts;
- **cash flow EXCLUDES chained transactions.** A chain is how this API models a transfer, and a
  transfer moves money between two containers the same user owns. Counting it reports the same
  money as income on one side and spending on the other: it nets out of `total_net`, but it
  inflates `inflow` and `outflow` and makes `savings_rate` describe nothing. The target is silent
  on this; excluding is the only reading under which the numbers mean what they are named;
- **`savings_rate` is `total_net / inflow * 100`**, and `null` when nothing came in. The target's
  own example (inflow 15, outflow 10, rate 15) matches no formula — 15 is just `inflow` repeated —
  and its notes already admit that section was copy-pasted. Recorded as a `DOC BUG` below;
- **`net_diff.percentage` is `null` when the window opened at zero.** Every gain from nothing is
  infinite growth; `direction` still carries the sign, so a client is not left guessing;
- **`comments` is a nullable STRING, not a list.** The target names it plurally but shows `null`
  rather than `[]`, and the neighbouring `analysis.comment` is a string. Reasons are joined rather
  than making every client branch on an array;
- **`balanced` asks two questions.** The identity `assets == liabilities + equity` may hold over a
  chart built on a posting whose own legs did not agree, so unbalanced dispatches are counted
  separately and either one unbalances the sheet. Both are DIAGNOSTICS — an unbalanced sheet is a
  state the system can be in, never a failed request;
- **the series is bucketed in the database.** `points` equal-width slices are computed with one
  grouped query and accumulated in Python, rather than one query per point or fetching every row;
- **one fold, one rate per currency.** `MoneyFolder` resolves a rate once per SOURCE currency and
  reuses it for every bucket, and it never rounds — rounding happens once, in the presenter, at the
  reporting currency's scale, so the error cannot compound across a hundred points;
- **a blank `currency_code` counts at face value.** The projection can leave one empty; dropping
  those rows would silently understate every figure they appear in;
- **no new cache counter.** The keys compose the `ver:transactions:` and `ver:accounts:` counters
  the write reactions already bump, so either changing invalidates every metric. A test asserts the
  two spellings still match the reaction side;
- `LimitPolicy` gained a `parameter` field so `points` rejects under its own name instead of
  blaming `limit`;
- `since` bounds `net_worth` and `cash_flow` only. `balance` is a snapshot of the chart as it
  stands and has nothing to bound.

> **DOC BUG.** `GET /metrics/cash-flow`'s example gives inflow 15.00, outflow 10.00, total_net 5.00
> and `savings_rate: 15` — which is `inflow`, not a rate. Either state the formula or fix the
> example; implemented as `total_net / inflow * 100` (75 for those numbers).

> **DOC BUG.** The target specifies no behaviour for transfers in cash flow, and the answer changes
> every figure on the endpoint. Implemented as "chained transactions are excluded"; if that is
> wrong the fix is one filter, but the contract should say which.

- **6.1 the `balance` section** — assets/liabilities/equity plus `balanced` and `comments`;
- **6.2 the `net_worth` section** — `since` and `points`, `net_diff.percentage` and `direction`
  (`flat` is a real value), a fixed-size `series` that is NOT a paginated collection;
- **6.3 the `cash_flow` section** — inflow/outflow/total_net plus `savings_rate` as a bare number;

All three convert to the user's preferred currency before aggregating, are cacheable, and carry
`meta.cached`. Cache keys include the reporting currency (Step 0.9 note).

---

## Phase 7 — Notifications to target shape
Model and stream exist; the shape does not.

**STATUS: implemented, all three steps.** The `DECIDE` below was answered as it recommends —
explicit columns. What the build settled beyond the steps as written:

- **the proto renames rather than adds.** `short` -> `title` and `message` -> `body` keep their
  field NUMBERS but change their JSON keys, and the outbox publishes proto JSON — so this is a
  breaking wire change for anything in flight. Taken deliberately: the alternative is carrying two
  spellings of the same field forever in a system with no deployed consumers to protect;
- **`severity` crosses the wire as a proto ENUM, not a string.** A bare string has no way to reject
  a typo at the schema boundary. It is stored and presented as the lower-case name; UNSPECIFIED
  reads as `info`, because a producer that never set the field is saying "ordinary", not "unknown
  urgency the client must handle";
- **`subject_type` stays an OPEN vocabulary.** The target's Enumerations table lists `severity` and
  deliberately omits this, so it is a plain string column rather than a choice field;
- **a half-filled subject presents as `null`.** A reference needs both halves to be followable, and
  `{"type": "wallet", "id": ""}` is not a deep link;
- **`payload` survives as a column and disappears from the wire.** It is the producer's own bag; the
  target's shape has no room for it and `subject` is what a client actually follows;
- **acknowledgement is idempotent in three places, not one.** The entity keeps the first timestamp,
  the repository's UPDATE is filtered to rows that carry none, and the read projection filters the
  same way — so neither a double-tapped bell nor a redelivered event can move the moment the user
  saw it. Ack answers 200 with the notification, never 409;
- **`GET /notifications/count` is deliberately uncached** and reads both figures in one aggregate.
  The badge goes stale the instant the stream delivers anything, so a cache would trade a cheap
  indexed count for a number wrong in a way the client cannot detect;
- **push-service now PROJECTS rather than forwards.** It used to relay raw outbox frames — proto
  message name as the `event:`, outbox event id as the `id:`, proto JSON as the body. It now emits
  `notification.created` / `notification.acknowledged` with the documented payloads, uses the
  NOTIFICATION id as the `id:` (which is the resume token), and fans one `NotificationsAcknowledged`
  batch into one event per id, because a client tracks notifications individually;
- **the stream drops what it does not document.** The route is `/notifications/stream`; forwarding
  wallet and transaction frames down it made the endpoint mean something other than its name. This
  is a behaviour change for anything that was reading those, and there is nothing else on the SSE
  route today;
- **`Last-Event-ID` is accepted and replays nothing.** push-service is a groupless broadcast
  consumer reading `AtEnd` with no retention, so "best effort bounded by server-side retention" is
  honestly zero here. Building a backlog store would make a deliberately stateless service
  stateful; the target already names refetching the list as the recommended reconnect path in every
  case. Recorded in API_DIFF.md;
- **heartbeat is 15s**, inside the documented "at least every 30 seconds". `X-Accel-Buffering: no`
  is now set on the response: Kong does not buffer by default, but nothing in the service can prove
  that about every intermediary, and a buffered stream is indistinguishable from a hung one;
- the batch ack **keeps taking an explicit list of ids**. "Acknowledge everything, filtered or not"
  is still open — see the KEEP note below. Both ack endpoints now answer with notification
  resources rather than a list of ids.

### Step 7.1 — Model
`short` → `title`, `message` → `body`, `is_read` (Bool) → `acknowledged_at` (nullable timestamp), and
new `severity` plus a polymorphic `subject {type, id}`. Migration on both sides plus the event
payload.

> **DECIDE.** `NotificationReadModel.payload` is a JSONField that could carry `subject` with no
> migration. Prefer explicit columns for `severity` and `subject_type`/`subject_id` — both are
> filterable, and a JSON path in a WHERE clause is the kind of thing that is fine until it is the
> slow query.

### Step 7.2 — Endpoints
`GET /notifications` with `acknowledged` and `severity` filters, `GET /notifications/count`
(non-paginated badge), `POST /{id}/ack` idempotent by nature — re-acking keeps the original
timestamp and returns 200, never 409. Ack emits `X-Write-Version`.

### Step 7.3 — Stream
`/events` → `/api/v1/notifications/stream`. Event names `notification.created` (full resource) and
`notification.acknowledged` (`{id, acknowledged_at}` only). `id:` is the notification id and the
resume token; honour `Last-Event-ID` best-effort. Heartbeat comment at least every 30 seconds
(already implemented — verify the interval). Confirm Kong does not buffer the stream.

> **KEEP.** `POST /notifications/ack` (batch) already exists and API_DEVELOPMENT.md lists
> "acknowledge all" as an open item. Keep it; it is ahead of both documents. It needs the one rule
> the open item flags: what "all" means when the list is filtered. Recommend "everything matching the
> body's filter, unfiltered means everything".

---

## Phase 8 — Actions
No dependency beyond Phase 0, but its producers (the scheduler, and later Automations' `raise_action`
effect) make it worth doing after Notifications so the two share their `severity` vocabulary in code
and not just on paper.

**STATUS: 8.1–8.3 implemented; 8.4 partially — see the gap at the end.** What the build settled:

- **`severity_rank` is the sentinel column Step 0.4 left open.** The queue leads with urgency, and a
  keyset cursor cannot carry an enum whose alphabetical order is not its urgency order (`critical`
  sorts below `info`). The rank is stored, indexed and cursored on; `ACTION_QUEUE` is
  `severity_rank DESC, created_at DESC, id DESC`. That answers the last row of the open-decisions
  table;
- **the collapse is enforced by a partial unique index**, not only by the read-then-write in the
  command: `(user, group_key) WHERE status = 'pending' AND group_key <> ''`. Two schedulers firing
  the same check concurrently cannot both insert;
- **`dismissal` is a flag on the stored resolution, never presented.** The target says the server
  "designates" one resolution as dismissal but gives the client shape no room for it, and hardcoding
  the id `"dismiss"` would make the vocabulary a magic string. It decides the resulting status and
  stops at the presenter;
- **`X-Write-Version` is omitted, not zeroed, when `applies` was false.** `CommandResponseMixin`
  gained an optional version for this: a header carrying a number the client cannot use would invite
  a `Read-At-Least` on a read that was never going to move;
- **the read projection answers only PENDING rows.** A redelivered `ActionResolved` therefore cannot
  restate a dismissal as a resolution or move `resolved_at`;
- **`user_external_id` is denormalised onto the action row.** `events.async` is keyed by it and the
  expiry sweep runs with no request to read it from; storing it beats a user lookup per swept row;
- **the sweep runs one saga per action, not one per batch.** A single transaction over the batch
  would roll back every expiry because of one unpublishable event, and the sweep would never make
  progress past that row;
- `ExpireLapsedActionsCommandHandler` is deliberately NOT a `CommandHandlerBase`: that contract
  answers one request with one write version, and a sweep answers none.

> **GAP (8.4).** The expiry sweep and the `group_key` collapse are built and running
> (`run_action_expiry_sweeper`, a plain interval loop as a management command — the same shape this
> service already uses for its consumers, rather than a new scheduler component). The **scheduled
> job that RAISES time-triggered actions is not**, and cannot be: the target's own example is "a
> subscription charging tomorrow against a wallet that cannot cover it", and neither subscriptions
> nor recurring charges are modelled anywhere in this system. `RaiseActionCommand` is the seam that
> job would call; what is missing is a data source to check, which is a slice of its own rather than
> a piece of Actions.

- **8.1** Action model: open `kind`, closed `source`/`severity`/`status`, `group_key` +
  `occurrences` + `last_seen_at`, `subject`, `money`, `expires_at`, `resolved_at`, and `resolutions`
  as a server-authored list;
- **8.2** `GET /actions` with `status` (default `pending`), `source` and `severity` filters, ordered
  by the severity RANK column from Step 0.4;
- **8.3** `POST /actions/{id}/resolve`: 422 `unknown_resolution`, 409 `action_already_resolved`, an
  emptied `resolutions` array on the way out, `X-Write-Version` only when `applies` was `true`,
  dismissal producing `dismissed` rather than `resolved`;
- **8.4** Producers: the scheduler job that raises time-triggered actions, the `group_key` collapse,
  and the expiry sweep that moves a lapsed action to `expired`;

No `/search`, no detail endpoint, no server-driven forms. All three are decisions in the target.

---

## Phase 9 — Automations
Depends on the shared filter registry (0.8), chains (3.7, for the `transfer` effect), notifications
(7) and actions (8) for `notify` and `raise_action`.

**STATUS: implemented.** Rules can be authored, read, edited and deleted, and the engine runs both
trigger types.

- **Step 0.8's "shared registry" became a shared LIBRARY**, `libraries/filter-grammar-py`. The
  registry alone was not enough: automations are authored on write-service and the grammar lived in
  read-service, whose tree nodes build Django `Q` objects. The library holds the operators, the
  per-resource field policies and a store-agnostic validator; read-service keeps its `Q` and
  Elasticsearch translation on top and imports the grammar. Duplicating the policy tables per
  service — the house style for `http_contract` and `money` — was rejected here because the failure
  it invites is silent: a rule would validate on save and never match on search. Decided with the
  user;
- **the library's errors are framework-free.** `FilterParseError` carries a `detail_code` STRING and
  a JSON path rather than inheriting DRF's `ValidationFailed`, because two services with two error
  contracts import it. Read-service renders them through a new `FilterParseErrorTranslator`; the
  string values ARE the Detail Codes table, so both mappings are identity lookups;
- **the condition is validated against the trigger's SUBJECT.** An `event` trigger checks against
  the transactions policy, a `schedule` trigger against wallets — so `set_category` on a scheduled
  rule fails with `effect_subject_mismatch` at CREATE time rather than silently at run time;
- **`params` must be EXACTLY what the effect documents.** An unknown key is a typo the user should
  hear about, not a silently ignored setting. `transfer` takes the same money grammar as the rest of
  the API, so a JSON number where an amount belongs is refused;
- **`AutomationRefusal` carries its own path and detail code**, so the exception handler renders it
  without re-deriving either. It is one dataclass rather than a family of exception classes because
  every refusal produces the same 422;
- **the read model is written by an upsert.** `trigger` and `effects` are replaced whole rather than
  merged — deep-merging a condition tree has no sane definition — so creation and update are the
  same projection write;
- **`runs` and `last_run_at` are projected, never derived.** `runs` counts matches that APPLIED
  effects, which only the engine can know, and it arrives on its own `AutomationRan` event;
- **a soft-deleted rule leaves the list but still resolves by id**, because DELETE answers with the
  rule it removed;
- `ENUM_NAME_OVERRIDES` had to be added to the write-service schema settings: three serializers now
  carry a field literally called `type`, and the generator was falling back to `Type00fEnum`.

Phase 9.3 — the engine — decided the following, all of which the target left open:

- **the engine reads the transaction back from Postgres** rather than matching against the event
  payload. `TransactionUpdated` carries only the amounts, so a condition on `category` would
  silently never match; and a rule should be evaluated against the transaction as it now STANDS,
  not as it was when the event was written;
- **matching is the grammar library's third resolution.** read-service resolves a tree to `Q` or to
  an Elasticsearch query — both ask a store. An automation asks about one transaction already in
  hand, so `filter_grammar_py.matches` walks the same tree under the same policy. Keeping all three
  together is what stops a rule from validating on save and matching differently at run time;
- **an absent field satisfies NOTHING, `neq` included.** A transaction with no category is not "a
  transaction whose category is not Dining" — it is one the rule has nothing to say about. An
  uncomparable stored value likewise fails to match rather than raising: a corrupt row is not
  something a user's rule should learn about;
- **a run is CLAIMED before its effects are applied**, under a unique key in a new `automation_runs`
  table. Kafka delivers at least once and the sweeper wakes far more often than `daily` means, so
  without a claim a `transfer` repeats. Claiming first trades a lost run on a crash for never moving
  money twice, which is the right way round for money;
- **the key decides what "again" means.** An event rule fires once per transaction, ever — otherwise
  fixing a typo would repeat a transfer, and two rules setting the same category would oscillate
  forever. A scheduled rule fires once per wallet per PERIOD, so the period is in the key and the
  sweeper can wake every minute, or catch up after an outage, without repeating or skipping one;
- **`origin` gained a third value, `automation`**, written by the `transfer` effect and skipped by
  the engine. This is the re-entrancy guard the run key cannot provide: a transfer creates NEW
  transactions with new ids, so without a mark a rule would fire on the money it just moved, then on
  that, forever. It is additive per the target's own rules, and the request serializer takes
  `CLIENT_ORIGINS` rather than the enum — claiming it would be a way to hide a transaction from
  every rule;
- **the event consumer starts at the END of the topic** (`auto_offset_reset: latest`). Automations
  are forward-only; a new consumer group reading from the beginning would apply every rule to every
  transaction the user ever made, destructively where `transfer` is involved;
- **`runs` counts only runs that applied EVERY effect.** A half-run keeps what it did, per the
  target, but does not count: `runs` is what tells the user a rule still works;
- **one failing rule does not stop the others**, and a condition its policy no longer accepts does
  not match rather than raising. A tightened policy must not become an outage across a user's whole
  rule set;
- **the counter and its `AutomationRan` row go out in ONE transaction**, not a saga — unlike every
  other write here. Both are Postgres, so `aatomic` already gives what a saga would have to
  compensate for;
- **`raise_action` groups by its rule** (`group_key: "automation:<id>"`), so a daily rule that keeps
  matching bumps one action's `occurrences` instead of appending an action a day — the collapsing
  behaviour `group_key` exists for. Its resolutions are the backend's, since a user-authored rule
  cannot define the choices offered to a user;
- **the scheduled runner is a sweeper, not a scheduler.** It asks every schedule on every pass and
  lets the run key decide what already happened, which is why it needs no due-date column and no
  leader election;

- **9.1** Model and CRUD. `trigger.event` / `trigger.schedule` both always present in responses,
  exactly one non-null; sending the wrong one for the declared `type` fails with
  `trigger_field_conflict`. `trigger` and `effects` are replaced whole on PATCH, never merged. No
  `/toggle` endpoint;
- **9.2** Effect validation against the closed vocabulary: `effect_unknown_type`,
  `effect_params_invalid`, `effect_subject_mismatch` at CREATE time, not at run time;
- **9.3** The engine: `background_workers/services/automation_engine` consumes the outbox topic and
  `automation_schedule` sweeps the scheduled rules, both running
  `application/commands/automations/engine/`. Evaluation is `created_at ASC`, last-write-wins,
  forward-only. `runs` counts matches that applied effects, not evaluations. A run that fails
  partway does not roll back its earlier effects. `TransactionMetadataUpdated` counts as
  `transaction.updated` alongside `TransactionUpdated`: the user wrote "when a transaction changes",
  not "when a column changes";

---

## Phase 10 — Webhooks completion
Most of this slice is built, including the parts that are hardest to retrofit.

- **10.1** `GET /webhooks/event-types` — non-paginated catalog served from one registry that the
  publisher also reads, so the two cannot drift;
- **10.2** `GET /webhooks/{id}/deliveries` with `status` and `event` filters. The delivery log lives
  in webhook-service's own Postgres, so this is a gateway route to that service rather than a
  read-service query. The payload is deliberately not returned;
- **10.3** Secret rotation grace period: two live secrets for 24 hours, a third rotation invalidating
  the oldest immediately;
- **10.4** Address guard in the sender: no redirect following, and the RESOLVED IP checked at
  connection time against loopback/private/link-local/unspecified ranges;
- **10.5** Contract details: 409 `subscription_exists`, detail code `unknown_event_type`, hard delete
  cascading to subscriptions while the log survives;
- **10.6** Field renames at the presentation layer: `is_active` → `enabled`;

> **KEEP.** `attempter.go` retries with `retryBackoff * attemptNumber` — linear backoff, not the flat
> 30 seconds the target describes and closer to the exponential backoff API_DEVELOPMENT.md asks for.
> Do not downgrade it to match the document; update the document's Retries section to describe what
> the sender actually does.

> **KEEP.** `sender.go` already signs `v1=` + HMAC-SHA256 over the raw body, which is the documented
> scheme. Nothing to build there.

> **KEEP.** `POST /webhooks/search` exists and the target does not mention it. A new endpoint is an
> additive change under the versioning rules, so it can stay inside v1. Keep it unless it costs
> something to maintain.

---

## Phase 11 — Assistant
Last, because a useful assistant cites resources from every other slice.

- **11.1** Message store, `GET /assistant/messages` (newest-first; the client reverses for display),
  `DELETE /assistant/messages` as a hard delete returning a count;
- **11.2** `POST /assistant/messages` as SSE: `accepted` first with both ids, `delta` increments,
  a terminal `message` carrying the authoritative text and `refs`, `error` as the failure terminal.
  The reply persists whether or not the client is listening; a failed generation is stored with
  `status: "failed"` and its partial text. 503 `assistant_unavailable` on an unreachable upstream,
  and a stricter rate-limit tier than the per-user default;
- **11.3** `GET /assistant/overview` — `signals` (preformatted display strings, the one deliberate
  formatting exception in the API) and `prompts`. Cacheable, carries `meta.cached`;
- **11.4** `refs` extraction into the flat `{type, id}` list. No inline anchors;

Neither SSE endpoint may be buffered by Kong — verify `X-Accel-Buffering: no` on this one the same
way the notification stream needs it.

---

## Closing steps
- Regenerate the OpenAPI schema (`drf-spectacular` is already wired in both services) and check it
  against the target document endpoint by endpoint;
- Contract tests for the conventions themselves, not just per endpoint: envelope shape, money
  grammar, timestamp format, cursor round-trip, error-code coverage. These are what stop the surface
  drifting one endpoint at a time;
- Add a test asserting the 507 fallback never reaches a client (see the note below);
- Retire the `/api/v1/reads` alias once no client uses it;

---

## Where the implementation is ahead of the target

Collected from the notes above, in the order they matter.

1. **Read-your-writes is fully built and matches the contract.** The gateway signs
   `X-Write-Version` as `{seq}:{hmac}` in `write-ral-version` and verifies `Read-At-Least` in
   `read-at-least`, injecting the caller's last known version when the header is absent. Write
   service stays ignorant of the secret and the wire format. This is exactly the target's "opaque,
   signed string" — no work needed.
2. **The staleness reroute is real, not hand-waved.** The target says the gateway "transparently
   reroutes to the write side". Our mechanism: read-service answers 507 when its projection has not
   caught up, and the `read-fallback` plugin re-issues the request against
   `/api/v1/fallback-reads/*`. The 507 is internal and must never surface — worth an explicit test,
   since the target correctly says no error code covers this case.
3. **Idempotency is done** (Phase 0.7) — only error codes and `meta.idempotent_replay` remain.
4. **Rate limit tiers already match the target table exactly** (Phase 0.6) — only headers and body
   shape remain.
5. **Search runs on Elasticsearch with its own RAL tracking.** The target is silent on storage.
   ES gives real `icontains` semantics rather than `LIKE '%…%'`, and `search_after` maps onto keyset
   cursors directly — the ES choice makes Step 0.4 easier on the search endpoints, not harder.
6. **The ImmuDB ledger** is a stronger audit position than the document assumes, and it is what makes
   the Step 3.1 split (immutable flow / mutable metadata) the right shape rather than a workaround.
7. **`occurred_at`** already distinguishes when a transaction happened from when it was recorded.
   The target only has `created_at`. Keep the column.
8. **Webhook delivery** already signs correctly and backs off linearly — ahead of both documents.
9. **Batch notification ack** already exists; API_DEVELOPMENT.md still lists it as open.
10. **The vertical slice layout** in read-service (`query_slices/<slice>/{dtos,query_handler,infra,http}`)
    and the command/query split in write-service are worth preserving as new slices are added. Every
    phase above assumes new code follows the existing structure rather than introducing a second one.

## Open decisions blocking specific steps

| step | decision needed                                                                 |
|------|----------------------------------------------------------------------------------|
| 0.8  | `details[].field` path syntax for a failure inside a filter tree                  |
| 0.9  | cache keys must include reporting currency                                        |

Also, in the target's Status Codes table, 403 is described as "authenticated but the resource belongs
to another user", which contradicts the Authentication section's rule that another user's resource
returns 404 so the API is not an existence oracle. Implement the 404 rule; the table row is the error.
