# Backend vs API_TARGET.md — the complete client-visible delta

Written to be handed to the frontend as the single input for an integration
plan. Everything here is observable from a browser: a path that does not exist,
a field spelled differently, a status code the target does not name, a header
you must send or read, or a behaviour you have to code around.

**Precedence.** Where this file and `API_TARGET.md` disagree, this file wins —
it describes what is deployed. Where this file is silent, the target holds: the
envelope, keyset cursors, money-as-string, RFC-3339 timestamps, the filter
grammar and the rate-limit tiers are all implemented exactly as specified.

**Sources.** Consolidated from `API_DIFF.md` (client-facing deltas),
`API_IMPLEMENTATION.md` (phase status and gaps), `infrastructure/kong/kong.yml`
and its plugins, and the two generated OpenAPI documents. Current as of
Phase 11.

---

## 1. Orientation: one origin, two services, three schemas

Everything is under `/api/v1` at the gateway. Behind it, Kong splits by
**HTTP method**, not by path:

| method                          | upstream                 |
|---------------------------------|--------------------------|
| `GET`                           | read-service             |
| `POST` on `/{resource}/search`  | read-service             |
| `POST`/`PUT`/`PATCH`/`DELETE`   | write-service            |
| `GET /notifications/stream`     | push-service (Go, SSE)   |
| `GET /webhooks/{id}/deliveries` | webhook-service (Go)     |
| `/chat/*`, `/assistant/*`       | ai-service (FastAPI)     |

`strip_path: false` on every route, so paths pass through unchanged. The client
sees one origin and never needs to know which service answered.

**Machine-readable schemas** are served per service and are clean (zero
generation warnings):

- `GET /api/schema/` on write-service — 36 paths, all mutations
- `GET /api/schema/` on read-service — 26 paths, all GETs plus the 3 searches
- `GET /openapi.json` on ai-service — FastAPI default

Their union is the HTTP surface. **Four things they do not tell you** — plan to
supply these by hand:

1. **Zero header parameters.** `Idempotency-Key`, `Read-At-Least` and
   `X-Write-Version` appear only in endpoint descriptions, never as
   `in: header`. Generated clients will not have them. Section 3 is the contract.
2. **No `507` and no `429` documented.** The declared codes are 200, 401, 404,
   409, 422 and 503. The staleness protocol (section 4) is invisible to codegen.
3. **18 `fallback-reads/*` paths in the write schema.** These are the gateway's
   internal reroute targets. **A client must never call them.** Strip them
   before generating.
4. **The Go and WebSocket surfaces are absent** — SSE, webhook deliveries and
   the assistant socket. Sections 7 and 8 are the only specification for those.

If you generate types: component names changed since the previous release. A
list item is `<Resource>Preview`, a detail item is `<Resource>Detail`, a search
hit is `<Resource>SearchResult`. Previously all three were `<Resource>Response`
and collided, so old generated types were wrong. Money is a single `Money`
component everywhere; auth is one `clerkBearer` HTTP bearer scheme.

---

## 2. Endpoint map

### 2.1 Paths in the target that do not exist

| target path | what to call instead |
|---|---|
| `POST /assistant/messages` | **WebSocket** `GET /api/v1/chat/advice`, send `{"text": "..."}`. Plain 404 with no error envelope if you call the REST path. See §8 |
| `GET /metrics/balance` | `GET /metrics?balance=true` |
| `GET /metrics/net-worth` | `GET /metrics?net-worth=true` |
| `GET /metrics/cash-flow` | `GET /metrics?cash-flow=true` |
| `GET /accounts/{id}/postings` | `GET /accounts/{id}` — postings are the embedded `history`, paged through the detail's own `limit`/`cursor` |
| `POST /automations/{id}/toggle` | `PATCH /automations/{id}` with `{"enabled": false}` — setting a field, not flipping one, because a toggle is not idempotent |
| `PATCH /transactions/{id}` with `new_amount` | `POST /transactions/{id}/adjust`. The key is **silently ignored** by PATCH, so a client on the old spelling changes nothing and never errors |

### 2.2 Paths that exist and are not in the target

`POST /transactions/{id}/adjust` · `POST /transactions/chains` ·
`DELETE /transactions/chains/{chain-id}` · `PUT /wallets/{id}` ·
`POST /wallets/search` · `POST /webhooks/search` · `POST /notifications/ack`
(batch) · `DELETE /notifications/{id}` · `GET /notifications/count`

### 2.3 Everything else is routed

Every other path in `API_TARGET.md` exists at the spelling the target gives it.
`GET /events` moved to `GET /notifications/stream`.

---

## 3. Headers — the contract codegen will not give you

### 3.1 Outbound

| header | when | notes |
|---|---|---|
| `Authorization: Bearer <clerk session token>` | every request | verified at the gateway |
| `Idempotency-Key` | **required** on `POST /transactions` and `POST /transactions/chains`; recommended on any mutation that moves money | one key per **logical operation**, stable across retries. One key covers a whole chain |
| `Read-At-Least` | optional | see §4 — the gateway injects it for you when absent |
| `X-Correlation-ID` | optional | echoed back; useful for support |

**`Idempotency-Key` must be stable across retries.** A fresh UUID per HTTP
attempt defeats the header entirely — the retry arrives as a new operation and
double-posts. Mint it when the user commits the action, not when the request
leaves.

### 3.2 Inbound

| header | meaning |
|---|---|
| `X-Write-Version` | opaque signed token on mutation responses. Send it back as `Read-At-Least` on the follow-up read to get read-your-writes. **Absent on `POST /actions/{id}/resolve` when the chosen resolution had `applies: false`** — nothing changed, so there is nothing to wait for |
| `Idempotent-Replayed: true` | a convenience mirror of `meta.idempotent_replay`. The meta key is the contract |
| `X-RateLimit-*`, `Retry-After` | see §5 |

CORS exposes exactly: `X-Correlation-ID`, `X-Write-Version`,
`Idempotent-Replayed`, `Retry-After` and the four `X-RateLimit-*` headers.
Allowed request headers: `Accept`, `Authorization`, `Content-Type`,
`X-Correlation-ID`, `Read-At-Least`, `Idempotency-Key`.

### 3.3 CORS — one thing to check first

The gateway sends `Access-Control-Allow-Origin: *` with **`credentials: false`**
and emits no `Access-Control-Allow-Credentials`. A browser request made with
`withCredentials: true` will therefore fail CORS outright. Auth is the bearer
token, not a cookie — send the token, leave credentials off.

### 3.4 User preferences come from the Clerk token — configure this first

The gateway reads `currency`, `timezone` and `language` from the verified
token's **`unsafeMetadata`** claim and forwards them as `X-User-Currency`,
`X-User-Timezone`, `X-User-Language`.

**Each header is set or CLEARED unconditionally.** If the Clerk JWT template
does not include `unsafeMetadata`, the claim is absent, the headers are cleared,
and every user silently gets `USD` / `UTC` / `en`. Nothing errors. Metrics come
back in the wrong currency and wallet-detail period boundaries resolve in the
wrong zone — both plausible-looking.

**Exact shape.** The gateway reads a **top-level JWT claim literally named
`unsafeMetadata`**, whose value is an object with these keys:

```json
{
  "unsafeMetadata": {
    "currency": "EUR",
    "timezone": "Europe/Berlin",
    "language": "de"
  }
}
```

In the Clerk JWT template that is `{"unsafeMetadata": "{{user.unsafe_metadata}}"}`.
The claim name is matched exactly and is **not** snake_case — `unsafe_metadata`
as a claim name will not be read.

**Whether the template already includes it: no, and it cannot be verified from
this repo.** The claim is configured in the Clerk dashboard, and nothing in the
backend requires or asserts it — the gateway treats an absent claim as
"preferences unset" and clears the headers. **Someone with Clerk dashboard
access must confirm the template.** The observable test: set a non-USD currency
on the user, call `GET /metrics`, and check the currency on the returned money
objects. If it is `USD`, the claim is not in the token.

**Per-field validation, values, and fallback:**

| field | format | validated against | falls back to |
|---|---|---|---|
| `currency` | ISO-4217, case-insensitive, trimmed | must be in `GET /currencies` (34 codes) | `USD` |
| `timezone` | IANA name | must load as a real zone | `UTC` |
| `language` | BCP-47 tag | 2–35 chars, alphanumeric between hyphens | `en` |

Each field falls back **independently** — a bad `timezone` does not affect
`currency`. Only non-empty strings are forwarded: a number, a null or `""` is
treated as unset. **A bad preference is never an error and never fails a
request** — it degrades presentation silently, by design, because
`unsafeMetadata` is client-writable and therefore untrusted input.

This is a Clerk dashboard change (JWT template), not a code change, and it
gates the correctness of every money figure in the app.

What the preferences decide:

- **`currency`** — the reporting currency for `GET /metrics`. There is
  deliberately **no `currency` query param**; a per-request override would be a
  second way to choose it and the two would disagree the moment one was cached.
- **`timezone`** — the calendar boundaries for `GET /wallets/{id}?period=`.
  Two clients in different zones legitimately see different figures for the
  same wallet and the same period.
- **`language`** — accepted and forwarded; nothing varies on it yet.

A preference change is **not an API write**, so nothing invalidates
server-side. After changing it, refetch. A cached response may still be
denominated in the currency preferred a minute ago — `meta.cached` tells you.

---

## 4. Staleness: the 507, the reroute, and the three holes

This is the single most important behaviour that codegen cannot see.

**How it works.** read-service answers `507` when its projection has not caught
up to the caller's write version. Kong's `read-fallback` plugin catches that,
rewrites the path to `/api/v1/fallback-reads/*` and re-issues against
write-service. The client sees one response and never the 507.

**It applies whether or not you send anything.** When `Read-At-Least` is
absent, the gateway looks up the user's last known write version and **injects
the header itself**. The gate is per-user and **global** — any write can make
any gated read take this path until the projection catches up. You do not opt
in and you cannot opt out.

**What this means for the client:**

1. **A rerouted read is slower than the read it replaces** — two upstream trips.
   A short client timeout will abort the fallback and surface a network error
   for a request that was about to succeed. Budget for it; a 5-second ceiling is
   too tight.
2. **A rerouted read always reports `meta.cached: false`.** Reads answered by
   the read side carry the real value.
3. **Three reads have no write-side counterpart, and fail loudly:**

   | read | what you get instead |
   |---|---|
   | `GET /accounts` | **404, no error envelope** |
   | `GET /accounts/{account-id}` | **404, no error envelope** |
   | `GET /metrics` | **404, no error envelope** |

   The reroute lands on a path that is not there. The resource exists. This is
   **transient** — it clears within moments of the write that caused it.
   **Retry rather than treating it as a missing resource, and do not cache it.**
   Accounts live in ai-service's database and Metrics needs the whole aggregate
   with currency conversion, so neither can be answered by write-service today.

4. **The three `/search` endpoints answer a real `507`, with an error envelope.**
   The plugin only re-issues GETs, and the write side has no Elasticsearch. A
   search sent immediately after a write may return `507`. This is permanent, not
   a gap. **Treat it as "retry shortly", never as a failure to show the user.**

   **Key on the status, not the code.** The body is:

   ```json
   { "error": { "code": "internal_error",
                "message": "Read model has not caught up to the required write version." },
     "meta": { "request_id": "...", "timestamp": "..." } }
   ```

   The exception carries `read_model_not_caught_up` internally, but the envelope
   renderer has no mapping for 507 and falls through to the generic
   `internal_error`. So `507` is the only reliable discriminator, and the code
   actively misleads — a client routing on `internal_error` will show a crash
   banner for a request that should be retried. Backend-side defect; the status
   is stable either way.

5. **A filtered page 2 of `GET /notifications` or `GET /webhooks` can be
   rejected as `cursor_mismatch` if it trips the gate.** Those two fallbacks do
   not bind the cursor to the active filters the way their read-side
   counterparts do, and they ignore the filters entirely. Known gap. Recovery is
   to restart the collection from page 1 without a cursor.

---

## 5. Rate limits

Two tiers, both at the gateway:

- **per IP** — 200/minute, 5000/hour (a floor that fires before token
  verification, so invalid tokens cannot burn CPU)
- **per user** — 60/minute, 1000/hour

`429` carries `Retry-After` and the `X-RateLimit-*` headers, all CORS-exposed.
Note that `429` is **not** in the OpenAPI documents.

---

## 6. Resource deltas

### 6.1 Money — read this before anything else

**`money.amount` is a decimal STRING and must never become a JS number.**
The schema says so explicitly: *"Canonical decimal string at the currency's own
scale — two fraction digits for USD, none for JPY. Never a JSON number."*
Parsing to float loses cents on ordinary values. Keep it a string end-to-end,
or use a decimal type; format for display using `decimals` from
`GET /currencies`.

The same applies to `rate` on `GET /currencies/convert` — a bare unpadded
string with up to 12 fraction digits — and to every rate in
`GET /currencies/rates/{code}`.

**`money.amount` is always a positive magnitude.** Direction comes from `type`
on transactions and from normal-balance conventions on metrics. There are no
negative amounts on the wire.

### 6.2 Transactions

- **A transaction is not a ledger row.** It is a mutable record (`name`,
  `category`, `evidence`, `origin`, `chain_id`) owning one or more **immutable**
  money flows. Creating appends a flow, adjusting appends the difference,
  cancelling appends an inverse. Nothing ever rewrites a flow — which is why
  `PATCH` is guaranteed never to touch money.
- **`type` is derived from the flow's sign**, never stored, so it cannot drift
  from the amount. `expense` is negative underneath, `income` positive.
- **A cancelled transaction still reports the amount it was FOR.** `DELETE`
  echoes that figure beside `deleted_at`, and so does detail. The wallet balance
  is a separate question and does return to where it stood.
- Cancelled transactions leave `GET /transactions` and search but **still
  resolve by id**. There is no `include_deleted` flag anywhere in the API.
- **`occurred_at` is a filter-only column and is currently a copy of
  `created_at`.** It exists in the read model and the search index, and it is
  filterable — but it is on **no response body** (no presenter emits it), it is
  accepted in **no request body**, and the projection writes
  `occurred_at = created_at` verbatim in both Postgres and Elasticsearch. So
  filtering on it works and returns exactly what filtering on `created_at`
  returns. It is forward-compatibility for a future "when the money moved"
  distinct from "when the row was written" — that distinction does not exist
  yet. **Do not build UI on it and do not offer it as a filter.**
- `GET /transactions/{id}` returns `postings: []` and `analysis: null` rather
  than omitting the keys, so you never branch on existence. Both are filled by
  the Accounts slice, which dispatches **after** the write returns — a
  transaction read immediately after creation legitimately shows an empty
  ledger for a moment. `evidence` returns `{"url": ...}` or null.
- Ordering: `created_at DESC, chain_id ASC NULLS LAST, id DESC`. Chain members
  share a commit timestamp so a transfer's legs arrive contiguously — though
  they may still straddle a page boundary.
- **`origin` gained a third value, `automation`**, server-authored. Treat it as
  an unknown-but-valid case if you switch on `origin`. `POST /transactions`
  rejects it.

**`POST /transactions/{id}/adjust`** — correcting an amount

```
POST /api/v1/transactions/{id}/adjust
{ "amount": "70.00" }
```

- `amount` is the new **TOTAL**, not a delta. A user correcting a receipt types
  the right figure, not the difference.
- Still a positive magnitude. **Direction cannot change here** — an expense
  stays an expense. To flip it, cancel and create the one you meant.
- Response is the preview shape with the new folded amount. The transaction
  keeps its `id`, `created_at` and its place in the feed.
- Absolute rather than incremental, so re-sending is a no-op and a retry cannot
  double-count.
- `409` if already cancelled.
- **The original is never rewritten and never cancelled.** Correcting 50.00 to
  70.00 leaves the 50.00 flow and adds a −20.00 beside it; the wallet balance
  moves by 20.00, not 70.00. Corrections compose.

**Chains** — how transfers are expressed

- `POST /transactions/chains` commits an expense on one container and an income
  on another, atomically. `after` references `temporary_id`s in the same request
  and is a **dependency, not a sequence number** — entries with no dependency
  commit in written order.
- Every leg shares one `created_at`.
- **`meta.transactions` cursors are always null.** The pagination triple is
  emitted because the target specifies it, but a chain holds at most 100 entries
  and all of them are in the response. **Do not build a paging loop against it.**
- There is **no endpoint that reads a chain by id.** To re-read one, filter
  `POST /transactions/search` on `chain_id`.
- A failure anywhere rolls the whole chain back and issues no `chain_id`.
  `error.details[].field` points at the offending entry by index, e.g.
  `transactions[1].after`.
- More than 100 entries is `422 chain_too_long`.
- `DELETE /transactions/chains/{chain-id}` cancels every leg. Repeating returns
  200 with the same body.

### 6.3 Wallets

- **`zero_balance` is a credit DATUM, not a floor.** It is the point at which
  the wallet holds none of the user's own money. Balance may go below it, and
  below it the user **owes** `zero_balance - balance`. What the user owns is
  `balance - zero_balance`. A fresh credit card with a 100 limit opens at
  balance 100 and owns 0; spend 30 and it owns −30. A cash wallet has
  `zero_balance` 0.
- **`money.amount` is the SPENDABLE balance, not the owned figure.** Both are
  sent side by side precisely so the client can derive the difference.
  **Do not build a client-side net worth that sums `money.amount` across
  wallets** — an unspent credit line is not the user's money. Metrics sums
  `balance - zero_balance` and treats the drawn portion as a liability.
- **`opening_balance` is POST-only and never echoed back.** It is not stored: it
  is realised as a real opening **transaction** at creation. Omitting it opens
  the wallet on its datum, owning and owing nothing. Expect that entry to appear
  in `GET /transactions`.
- Ordering `favorite DESC, created_at DESC, id DESC`. The leading key is applied
  **after** filtering, so a favourite that does not match a search filter is
  absent like any other non-match.
- **`DELETE` closes a wallet only when `balance == zero_balance`** — settled in
  both directions. Money still in it and debt still owed on it both answer
  `409 wallet_not_empty`. Closing an already-closed wallet is 200, and stays 200
  even if the balance later drifts.
- A closed wallet leaves lists and search but **still resolves by id**.
- **`GET /wallets/{id}` emits `period`, not the target's `last_month`**, and
  takes `?period=last_week|last_month|last_year|all_time` (default
  `last_month`). The target hardcodes the previous calendar month with no way to
  ask for anything else; the key was renamed because a field called `last_month`
  holding nineteen months would be actively misleading.
- Every window except `all_time` is a **CALENDAR** window, not a rolling day
  count: `last_month` on the 3rd is the whole previous month, not the preceding
  30 days. Windows are half-open so consecutive ones tile without
  double-counting. `all_time` genuinely drops both bounds.
- Boundaries resolve in `X-User-Timezone` (see §3.4).
- `period.inflow` / `period.outflow` are positive magnitudes in the **wallet's**
  currency. Nothing is converted — this is wallet detail, not Metrics.
- The window is echoed in `meta.period`. An unknown value is **422
  `validation_failed`** on field `period`, not a silent fallback.
- `period` is **never cached** even when `meta.cached` is true — that flag
  reports on the wallet body.
- `GET /wallets/{id}` embeds **`recent`**: the wallet's own feed in the same
  preview shape and order as `GET /transactions`, paged through the endpoint's
  `limit`/`cursor` and reported under `meta.recent`. Cancelled transactions
  excluded. Computed per request, never cached.
- **`PUT /wallets/{id}`** is not in the target. It replaces the whole editable
  representation, so an omitted field **resets to default** — unlike `PATCH`.

### 6.4 Goals

- Shape matches the target: `id`, `name`, `url` (always null), `currency`,
  `finish_at`, three structural timestamps, `target` and `progress` as money.
- **`progress` is derived and never writable.** `PATCH` accepts a `progress`
  key and **discards** it rather than rejecting.
- **`currency` is fixed at creation** and not accepted by `PATCH` — both
  `target` and `progress` are denominated in it.
- **A goal id is accepted anywhere `wallet_id` is.** Funding a goal is an
  ordinary `POST /transactions/chains` transfer; draining is the same reversed.
  **There is no contribution endpoint.**
- A transaction moving money in a goal still renders it under the key
  **`wallet`** — that is what the target specifies. Treat the two
  interchangeably; the container's kind is not part of the transaction shape.
- `DELETE` refuses non-zero `progress` with `409 goal_not_empty`. Posting to a
  **closed** goal is `409 wallet_closed` — deliberately the same code the target
  defines for a soft-deleted wallet, not a new one.
- `GET /goals/{id}` embeds **`history`**: one entry per transaction touching the
  goal, in the target's entry shape (`title`, `debit`, `created_at`,
  `source_transaction`, `icon`, `money`), paged under `meta.history`. `debit` is
  true when money moved **in**. **`icon` is always `""`** — nothing assigns one.
- **History entries carry an `id`**, which the target's examples omit; a
  keyset-paginated collection needs a stable anchor.
- **There is no `POST /goals/search`**, matching the target.

### 6.5 Accounts

- **Read-only.** Nothing creates, edits or deletes one — they are derived from
  transactions.
- **The balance is a `money` object, not a bare decimal.** Every account is
  denominated in a single **book** currency (`USD` today); postings are
  converted before summing. So `money.currency` is the book currency, **not**
  the currency of the transactions behind it. A history entry carries the
  currency of its own transaction, so the two legitimately differ inside one
  response.
- **The shape carries `created_at` and `updated_at`.** The target's example has
  no timestamps yet sorts on `created_at`. There is no `deleted_at` — an account
  is never deleted.
- Ordering `created_at DESC, id DESC`. **`group` filters and does not order** —
  assets do not lead liabilities.
- **`lowbar` compares MAGNITUDES, not signed balances.** A liability's balance is
  negative, so a signed comparison would empty that group the moment you set any
  threshold. `?lowbar=1.00` hides everything smaller than 1.00 in either
  direction.
- `lowbar` is read in `currency` (default `USD`) and converted into each
  account's book currency before comparing. Unknown `currency` is
  `422 unsupported_currency`; a `lowbar` finer than that currency's scale is
  `422 amount_precision`. `meta` echoes both. A `lowbar` of `0` — the default —
  excludes nothing, reaches no rate feed, and so can never fail with
  `rate_unavailable`.
- **`meta.groups` ignores `group` but honours `lowbar`.** The target only
  specifies the first; ignoring the threshold too would make a tab advertise a
  count that selecting it does not produce. Every group is present, including
  empty ones.
- Accepted `group` values: `all` (default), `assets`, `liabilities`, `equity`.
  Unknown is `422 validation_failed`.
- `GET /accounts/{id}` embeds `history` — the postings dispatched into the
  account, in the target's entry shape, paged under `meta.history`. `debit` is
  true when the leg debits the account. Entries carry an `id`.
- **`analysis.balanced` on a transaction is a diagnostic, never an error.** Most
  often `false` when the two legs landed in different currencies.
- **The ledger is not reachable through `Read-At-Least`.** That header tracks
  write-service's outbox; ai-service dispatches from its own sequence, after
  your write returned. A satisfied `Read-At-Least` for a transaction says
  nothing about its postings having landed. **Poll rather than expecting
  read-your-writes on the ledger.**

### 6.6 Metrics — three endpoints collapsed into one

```
GET /api/v1/metrics?balance=true&net-worth=true&cash-flow=true
```

The three sections read the same rows and differ only in folding, so splitting
them cost three round trips, three authentications, three cache entries and
three scans for one screen. Merged, they come out of a single grouped query
with one rate lookup per currency.

- Each selector is an independent **boolean defaulting to `true`** — a bare
  `GET /metrics` returns all three, which is the call this endpoint exists for.
  Accepted: `true/false`, `1/0`, `yes/no`, `on/off`; anything else is 422
  against that selector's own name.
- **An excluded section is `null`, not missing.** All three keys are always
  present.
- JSON keys are `balance`, **`net_worth`**, **`cash_flow`** — snake_case like
  everything else. The **query params keep the target's hyphenated spelling**
  (`net-worth`, `cash-flow`) because that is what its paths were called.
- Dropping a section really skips its work.
- `meta` carries `since`, `points`, `sections`, `cached` on every response.
- Asking for nothing is a 200 with three nulls, not an error.
- Every figure is in the **preferred currency** (§3.4). No `currency` param.
- An amount whose denomination the backend never learned is counted at face
  value rather than dropped, so a figure is never silently understated.

**`balance`**
- Amounts are **normal-balance positive**: a liability owing 20 is `"20.00"`,
  not `"-20.00"`. The identity to check is `assets == liabilities + equity`.
- `balanced` is false if that identity fails **or** if any transaction posted
  with disagreeing legs. Both are diagnostics; an unbalanced sheet is still 200.
- **`comments` is a string or null, not an array.** The target names it plurally
  but shows `null`; reasons are joined into one string so you never branch.

**`net_worth`**
- The running total of every non-cancelled transaction against your containers.
  **A transfer does not change it** — both legs are yours and they cancel.
  Computed from transactions, not the ledger, so it is correct before the
  accounts slice has dispatched.
- `since` bounds `net_worth`'s series and `cash_flow`. It does **not** bound
  `balance`, a snapshot of the chart as it stands.
- `since` selects the **window**, not the balance: money held before it still
  counts toward `money`. What it bounds is `net_diff` and `series`.
- With no `since`, the window opens at your **first transaction** rather than
  padding the front with zeroes.
- `series` has exactly `points` entries and is **not paginated** — no cursors.
  Each point is the running total at the **end** of its slice, so the last point
  equals `money`.
- `points` defaults to 10 and is **clamped** to 1..100, not rejected;
  `meta.points` reports what was applied. A non-integer is 422 on `points`.
- **`net_diff.percentage` is null when the window opened at zero** — any gain
  from nothing is infinite growth. `direction` still tells you which way, and
  `flat` is a real value.

**`cash_flow`**
- **Transfers are excluded from both halves.** A chain moves money between two
  containers you already own; counting it would report the same money as income
  and as spending.
- `inflow` and `outflow` are both **positive magnitudes**.
- **`savings_rate` is `total_net / inflow * 100`** — a bare number, not money.
  The target's example shows `15` for inflow 15 / outflow 10, which is `inflow`
  repeated rather than any rate; the same figures return `75.0` here.
- **`savings_rate` is `null` when nothing came in**, not zero. A rate against no
  income is undefined, and zero would claim you saved nothing when there was
  nothing to save. **Guard this before formatting.**

### 6.7 Actions

- **The queue leads with urgency**: `severity DESC, created_at DESC, id DESC`.
  This is the one collection that does not order purely by recency — a list to
  be worked through, not a feed to be read.
- **`status` defaults to `pending`.** Pass `resolved`, `dismissed` or `expired`
  for those slices. `source` and `severity` default to absent, meaning all.
  Unknown values are 422 against that param's own name.
- **Render one button per entry in `resolutions` and never switch on `kind`.**
  `kind` is an open vocabulary — use it to pick an icon with a generic fallback.
  Deriving labels or button counts from it reintroduces the coupling this shape
  removes. `resolutions[].intent` is a rendering hint, not behaviour.
- **`money` is in the currency the action concerns**, not the reporting
  currency. Nothing is converted. `null` when the action is not about an amount.
- `group_key` collapses recurring conditions onto one row: a daily check bumps
  `occurrences` and `last_seen_at` rather than appending an action per run.
  `null` means it does not recur, and `occurrences` is 1 for those, never 0.
- **No `/search` and no detail endpoint**, matching the target. The list row
  carries the entire resource.

**`POST /actions/{action-id}/resolve`**
- Returns the answered action with **`resolutions` emptied** — an empty array
  rather than a stale list is what stops you re-rendering dead buttons.
- **`X-Write-Version` only when the chosen resolution had `applies: true`.**
- Choosing the resolution the server designates as dismissal produces
  `status: "dismissed"`; every other choice produces `"resolved"`. Which one
  that is is not exposed — render buttons either way.
- `resolution_id` must be one offered on **that** action; anything else is
  `422 unknown_resolution`, including an id valid on a different action.
- Answering an already-answered, dismissed or **expired** action is
  `409 action_already_resolved`.
- A resolved action is **not** soft-deleted: `deleted_at` stays null and
  `status` carries the queue state.

**Expect an empty queue.** The write path, the recurring collapse and the expiry
sweep are all built and running, but no scheduled check exists to raise
time-triggered actions, and the assistant does not raise them yet. Build the UI;
do not expect data to exercise it.

### 6.8 Automations

- `trigger.filter_body` is the **same filter tree** the `/search` endpoints
  take, checked against the policy of the trigger's **subject**: an `event`
  trigger against transactions, a `schedule` trigger against wallets. Failures
  carry the same `filter_*` detail codes as search, with a JSON path **into the
  tree** (`trigger.filter_body.and[1].or[0].operator`) so you can highlight the
  exact condition.
- **`filter_body: null` means "always".** An empty group (`{"and": []}`) is
  refused rather than meaning the same thing.
- **Requests supply ONE of `trigger.event` / `trigger.schedule`; responses carry
  both**, the inapplicable one `null`, so you read `trigger.schedule` without
  guarding. Sending the one that does not match the declared `type` is
  `422 trigger_field_conflict`.
- **`effects` is a closed vocabulary and `params` is validated by exact set
  equality.** Each entry is `{"type": ..., "params": {...}}`. The schemas type
  `params` as `additionalProperties: {}` because DRF passes it through as a
  plain dict and the **domain** validates it — the real contract is below.

  `set(supplied_keys) == required_keys`. There are **no optional params on any
  effect**: a missing key and an extra key both fail the same way, with
  `422 effect_params_invalid` and a reason naming the exact expected set.

  | `type` | `params` | applies to |
  |---|---|---|
  | `transfer` | `{from_wallet_id, to_wallet_id, money}` | both triggers |
  | `notify` | `{severity, title}` | both triggers |
  | `raise_action` | `{severity, title, body}` | both triggers |
  | `set_category` | `{category}` | **`event` triggers only** — on a `schedule` rule it is `422 effect_subject_mismatch` |

  Value rules:
  - `from_wallet_id` / `to_wallet_id` — UUID strings, and they must **differ**
    ("A transfer needs two different wallets"). A goal id is accepted, as
    everywhere a `wallet_id` is;
  - `money` — exactly `{amount, currency}`, no more keys. `amount` **must be a
    decimal string**, not a JSON number (`{"amount": 200.0}` is refused;
    `"200.00"` is accepted) and must be **> 0**. `currency` is a 3-character
    alphabetic code;
  - `severity` — one of `info`, `warning`, `critical`;
  - `title`, `body`, `category` — non-empty strings after trimming.

  Errors carry a JSON path into the effect, e.g. `effects[0].params.money.amount`.
- An effect that cannot apply to the trigger's subject is
  `422 effect_subject_mismatch` **at create time** — `set_category` on a
  scheduled rule, for instance.
- `effects` needs at least one entry.
- **`trigger` and `effects` are replaced WHOLE** when supplied, never merged.
  There is no way to say "change the third leaf" — send the complete new tree.
- **`DELETE` is a soft delete** returning the removed rule. It leaves
  `GET /automations` but **still resolves by id**. Nothing it already did is
  reverted.
- Ordering `created_at DESC, id DESC` — the **reverse** of evaluation order. The
  list shows newest first because that is how you think about rules; the engine
  runs oldest first so later rules override earlier ones. Say so in the UI if
  you show order.
- `enabled` is a **tristate** filter: absent means both.
- `icon` is free-form with a client-side registry, never validated server-side.

**What running a rule means** — three things the target leaves open:

- **An event rule fires ONCE per transaction, ever.** Editing a transaction a
  rule already saw does not run it again — otherwise fixing a typo would repeat
  its `transfer`. A rule created **after** a transaction never sees it. Rules
  are forward-only.
- **A scheduled rule fires once per wallet per period**, the period being the
  calendar one — a date for `daily`, an **ISO week** (Monday-based) for
  `weekly`, a month for `monthly`. A user with three wallets sees three runs a
  day from one daily rule.
- **`runs` counts only runs that applied EVERY effect.** A run that failed
  partway keeps what it already did but does not count. A rule that matched a
  thousand times and always failed reports `0`.

Three recognisable products of a rule:

- **`transfer` creates transactions with `origin: "automation"`** (§6.2).
- **`raise_action` produces an action with `kind: "automation"`** and
  `source: "scheduler"`, grouped by the rule that raised it. Its `resolutions`
  are the backend's — an acknowledgement and a dismissal, neither of which
  `applies` — because a user-authored rule cannot define the choices offered to
  a user.
- **`notify` writes its own `body`**, naming the rule that fired. The rule
  supplies `severity` and `title` and nothing else. There is no template string
  anywhere in the API.

`runs` and `last_run_at` are projected from the engine, so they arrive a moment
after the run. **`X-Write-Version` does not cover them** — no request of yours
caused the run.

### 6.9 Notifications

The old `short` / `message` / `is_read` fields and the free-form `payload`
object are **gone from the wire**, and `only_unread` with them. The shape is
now `severity`, `title`, `body`, `subject`, `acknowledged_at` plus the three
structural timestamps.

- **`acknowledged_at` is a timestamp, not a boolean.** `null` means unread. It
  records when the user saw it, so it never moves: acknowledging twice keeps the
  first value, and so does a redelivered event.
- **`acknowledged` is a TRISTATE** filter. Absent means both, which is not the
  same request as `acknowledged=false`. `severity` filters to `info`, `warning`
  or `critical`; unknown is 422 against that param's own name.
- **`severity` does not reorder the feed.** Ordering is the global default,
  `created_at DESC, id DESC` — a feed to be read, not a queue to be worked
  through. A `critical` from Tuesday does not outrank an `info` from this
  morning.
- **`subject` is `null` unless both halves are present.** A `{type, id}` with an
  empty id is not a deep link.
- `payload` is stored but never returned. Deep-link to `subject`.
- **Both ack endpoints return notification resources**, not
  `{"acknowledged_ids": [...]}`. Single ack returns the one; the batch returns
  every notification named in the request, in list shape.
- `POST /notifications/{id}/ack` is idempotent by nature and needs no
  `Idempotency-Key`. Re-acking is **200 carrying the original
  `acknowledged_at`**, never 409. There is no un-acknowledge.
- `POST /notifications/ack` (batch) takes an explicit list of ids.
  **"Acknowledge everything", filtered or not, does not exist yet.**

**`GET /notifications/count`** returns `{"unacknowledged", "total"}` with an
empty `meta`. Deliberately uncached, both figures in one query so the badge can
never exceed the total. **The value goes stale the moment the stream delivers
something — increment locally on arrival rather than refetching per event.**

### 6.10 Currencies and rates

- **`decimals` is the authority for rendering every amount in that currency.**
  Fetch `GET /currencies` before anything that formats money. JPY has no
  fraction digits; USD has two.
- **`symbol` is `""` for any code with no established symbol.** Fall back to the
  `code` rather than rendering an empty span.
- The table is **34 codes**, not the target's example count of 40. It is
  whatever the endpoint returns — **do not hardcode a list.**
- **`GET /currencies` is not paginated.** `meta.limit` and both cursors are
  `null`, `meta.total` counts everything returned, and there is **no
  `meta.cached` key on it at all**.
- **`GET /currencies/rates/{code}` takes `target` in either spelling.**
  `?target=RUB&target=EUR` and `?target=RUB,EUR` mean the same thing.
  `meta.target` echoes the normalised, upper-cased list, or `null` when you
  asked for the whole map.
- **An unknown code in `target` fails the WHOLE request** with
  `422 unsupported_currency` rather than returning the others. A silently
  missing entry cannot be told apart from a currency the feed does not quote.
- **A code in `GET /currencies` is not a promise of a rate.** The currency table
  and the rate feed are different sources. A listed code the feed does not quote
  answers **`409 rate_unavailable`** — retrying later is correct, it is not a
  client error. `422 unsupported_currency` is the one meaning "fix the code".
- **Rates are never stale-but-served.** If the feed has not published inside its
  freshness window, both rate endpoints answer `409 rate_unavailable` rather
  than handing back an old number. **Show "rate unavailable", not a figure with
  no timestamp.**
- **The upstream feed publishes once a day.** `meta.fetched_at` is the feed's
  publication time, not when the response was built, so it will routinely be
  hours old. Do not treat a past `fetched_at` as an error, and do not poll
  faster than the data changes.
- **`rate` is not money and `to` is authoritative.** `GET /currencies/convert`
  returns `from` and `to` as money objects at their own scales, plus `rate` as a
  bare unpadded string with up to 12 fraction digits and no currency. **Render
  `to`** — multiplying `rate` client-side can land on a different last digit,
  because the server rounds once, half-up, at the target currency's scale.
- **`amount` is validated against `from_code`'s scale, not `to_code`'s.**
  `?from_code=USD&amount=100.005` fails `422 amount_precision`; so does
  `?from_code=JPY&amount=10.5`.
- **None of the three endpoints honours `Read-At-Least`.** They carry no
  user-owned data, so they never answer 507 and never need the reroute.

### 6.11 Webhooks — breaking rename since the previous release

- **`is_active` is now `enabled`**, on the resource and on both bodies.
  `POST /webhooks` and `PATCH /webhooks/{id}` accept it, so an endpoint can
  finally be paused without deleting it. `GET /webhooks?enabled=` filters on it
  as a **tristate**. `POST /webhooks/search` filters on `enabled` too.
- **`deleted_at` is gone from webhook resources.** Webhooks are hard-deleted and
  the key was always null; it is no longer sent.
- **Subscriptions spell the event type `event`, not `event_type`** — in the
  `POST /webhooks/{id}/events` body as well as in responses. `is_active`,
  `updated_at` and `deleted_at` are gone from the subscription shape, which is
  now exactly `{id, webhook_id, event, created_at}`.
- **`GET /webhooks/{id}/events` is NOT paginated**: everything is returned with
  `meta.limit: null` and both cursors null. The target paginates it.
- **`GET /webhooks/event-types` serves five types, not the target's six.**
  `goal.reached` is absent — nothing publishes it, and advertising a
  subscription that would never fire is worse than a short catalog. Live:
  `transaction.created`, `transaction.updated`, `transaction.deleted`,
  `wallet.created`, `wallet.updated`. **Render from this endpoint, do not
  hardcode.**
- **`GET /webhooks/{id}/deliveries` is answered by a different service**, so its
  `meta` has **no `cached` key**. Everything else matches: `status` and `event`
  filters, keyset `cursor`, `limit` capped at 100, payload deliberately absent,
  and the log survives its endpoint's deletion. `status` accepts the five
  documented values; a sixth is 422. `next_attempt_at` and `last_error` are
  `null` on a finished delivery rather than blank.

---

## 7. Live channels

### 7.1 SSE — `GET /api/v1/notifications/stream`

Moved here from the target's `/events`.

| event | payload |
|---|---|
| `notification.created` | the **full** notification resource, identical to one element of `GET /notifications` — prepend it without a follow-up request |
| `notification.acknowledged` | `{id, acknowledged_at}` only. One frame **per notification** even when several were acknowledged together |

- The SSE `id:` is the **notification id**, not an internal event id.
- **The stream carries only these two events.** It used to relay every outbox
  frame for the user — `TransactionCreated`, `WalletUpdated` and the rest. Those
  are gone. Ignore unrecognised event names as the target requires, but **do not
  expect domain events among them.**
- **`Last-Event-ID` replays nothing.** push-service is a stateless broadcast
  consumer reading from the live end of the topic and keeps no backlog. Anything
  produced while disconnected is lost. **Refetch `GET /notifications` after
  every reconnect** — the target already names this as the safe path.
- Heartbeat comment lines arrive every 15 seconds, inside the documented 30, and
  `X-Accel-Buffering: no` is set so no intermediary can buffer the stream into
  looking hung.

### 7.2 Outbound webhooks (if you build a receiver)

- Deliveries are signed over **`"{timestamp}.{body}"`** and now carry
  `X-Webhook-Timestamp`. A receiver written against the previous release —
  which signed the bare body and sent no timestamp — **must be updated**, and
  should reject requests whose timestamp is more than five minutes off its own
  clock.
- **`X-Webhook-Delivery` now carries the `event_id`**, not the delivery row's
  id, so it repeats across retries of one event and is the value to deduplicate
  on.
- The body is the documented envelope `{id, event, created_at, data}`. **Caveat:
  `data` carries the domain event's own fields, close to but not identical to
  the resource this API returns** — a transaction arrives with
  `transaction_id`, `amount` and `currency_code` rather than `id` and a `money`
  object. Treat `data` as the event, not as a resource you can hand to code
  written against `GET /transactions/{id}`.
- **Rotating a secret keeps the previous one valid for 24 hours.** Hold both and
  accept a match against either. Rotating again inside the window invalidates
  the older immediately — only two are ever live.
- Delivery backs off **linearly**, not the flat 30 seconds both documents
  describe.

---

## 8. The assistant is a WebSocket

**`POST /assistant/messages` does not exist and never will in v1.** A request to
it gets a plain 404 with **no error envelope**.

Open **`GET /api/v1/chat/advice`** — the socket that was already there — and
send `{"text": "..."}`.

> **Blocker: a browser cannot authenticate this socket today.**
>
> The gateway's `clerk-jwt` plugin extracts the bearer token from the
> **`Authorization` header only** — there is no query-parameter fallback and no
> `Sec-WebSocket-Protocol` fallback. ai-service itself only reads the
> `X-User-Id` header Kong injects after verifying, and closes with **1008
> (policy violation)** when it is absent.
>
> The browser `WebSocket` constructor cannot set request headers. So
> `new WebSocket('wss://…/api/v1/chat/advice')` is refused at the gateway with
> 401 before ai-service is reached, and there is no client-side workaround.
> **Unblocking this needs a backend change** — accept the token via
> `Sec-WebSocket-Protocol` (the conventional trick) or via a query parameter on
> the upgrade request. Node and native clients that can set headers are
> unaffected.
>
> **The SSE stream has the same root cause but is workaroundable.** Native
> `EventSource` also cannot set headers, so `GET /notifications/stream` fails
> the same way — but a fetch-based SSE client can set `Authorization` and works
> against the gateway as it stands. Plan for one; escalate the other.

Replies are frames shaped `{"event": ..., "data": {...}}`, carrying the target's
own event names in the target's order:

| event | `data` |
|---|---|
| `accepted` | `{user_message_id, message_id}` — both messages are persisted |
| `delta` | `{text}` — an increment. Concatenate in arrival order |
| `message` | the finished message, with `refs`. **Replaces** the accumulated text |
| `error` | `{code, message, message_id}`. Terminal for the turn |

Everything the target promises about the exchange holds: `accepted` arrives
before any generation, so a client that drops immediately still knows both ids;
`delta` carries text only; the terminal `message` repeats the full text because
`refs` are not known until the end; and the reply is persisted whether or not
you are still listening, so a dropped connection means refetching
`GET /assistant/messages`, never re-sending.

Beyond the transport:

- **The socket stays open after a turn.** `error` is terminal for that reply,
  not for the connection — send another `{"text": ...}` and the conversation
  carries on. A frame no handler understands closes the socket with **1003**.
- **`Idempotency-Key` is not supported here.** A WebSocket frame carries no
  headers. Send a message twice and you get two turns.
- **No stricter rate-limit tier on sending.** The gateway limits the handshake,
  not the frames.
- **`assistant_unavailable` is an `error` frame code, not a 503.** There is no
  HTTP response to put a status on.
- **The reply is canned.** No model is wired: the assistant answers
  `"Received message: {your text}"`, streamed as several deltas. **`refs` are
  still real** — any transaction or account id in the reply that belongs to you
  comes back as a chip, so the citation path is live even though the wording is
  not. Build the chips.
- **`GET /assistant/messages` has no `meta.cached`.** It is not cached.
- **`GET /assistant/overview` carries `meta.cached`, but the cache is per server
  process**, not shared. Two requests seconds apart can both report
  `cached: false` if they land on different replicas.
- **`signals` are three fixed labels** — `Spend vs last month`, `Uncategorised`,
  `Recorded this month` — not the target's examples. **`value` is preformatted
  display text and must not be parsed**: it can read `+38%`, `no baseline yet`,
  `nothing yet` or `3 transactions`. The spend comparison is computed within a
  single currency and the months are calendar months **in UTC**, not in the
  timezone preference.
- **`prompts` adapt slightly** — a "still need a category" suggestion when you
  have uncategorised transactions, a "record your first transaction" one when
  the ledger is empty.

---

## 9. Request bodies

| endpoint | body |
|---|---|
| `POST /transactions` | `{name, wallet_id, currency, amount, type, origin?, category?, evidence?}`. `amount` positive, `type` states direction. **`Idempotency-Key` required.** `origin` accepts `manual` and `scanned` **only** — `automation` is server-authored |
| `PATCH /transactions/{id}` | `{name?, category?, evidence?}` and nothing else. **`new_amount` is gone and sending it changes nothing** |
| `POST /transactions/{id}/adjust` | `{amount}` — the new total, positive magnitude |
| `POST /transactions/chains` | `{transactions: [...]}`, each entry a `POST /transactions` body plus `temporary_id` and `after`. At most 100. **One `Idempotency-Key` covers the whole chain** |
| `POST /wallets` | `{name, currency, category?, color?, zero_balance?, opening_balance?}`. `color` is validated as CSS hex (`#RGB` / `#RRGGBB` / `#RRGGBBAA`) — the target shows one but names no format |
| `PATCH /wallets/{id}` | `{name?, favorite?, category?, zero_balance?, color?}`. Every field optional, omitted fields left alone, `{}` is a legal no-op. **Renamed `new_name` → `name` in Phase 2; a client still sending `new_name` silently changes nothing** |
| `PUT /wallets/{id}` | `{name, currency}` plus the same optional metadata. **An omitted field RESETS to default.** A different currency than the wallet was created with is 422 |
| `POST /webhooks` | `{title, url, enabled?}` (defaults `true`) |
| `PATCH /webhooks/{id}` | `{title?, url?, enabled?}` |
| `POST /webhooks/{id}/events` | **`{event}`** — not `event_type` |

`zero_balance` and `opening_balance` are flat decimal strings validated against
the wallet currency's scale.

---

## 10. Errors and filters

### 10.1 Codes beyond the target's table

Clients must tolerate unknown codes anyway, but these are actually emitted:

| code | status | meaning |
|---|---|---|
| `service_unavailable` | 503 | a dependency is down — retrying is correct |
| `insufficient_funds` | 409 | the wallet is short |
| `conflict` | 409 | a state conflict the contract names no specific code for |

One extra `details[].code`: **`invalid`**, for a field of the wrong shape — the
Detail Codes table has no generic member for that.

Also: the target's Status Codes table says 403 means "authenticated but the
resource belongs to another user". That contradicts its own Authentication
section, which says another user's resource returns **404** so the API is not an
existence oracle. **The 404 rule is what is implemented.** The table row is the
error.

### 10.2 Filterable fields

The full filter vocabulary per resource, with the operators each field accepts.
A field outside its resource's list is `422 filter_unknown_field`; a valid field
with an operator it does not accept is `422 filter_operator_not_allowed`.

**`POST /transactions/search`** — ten fields, one more than the target:

| field | operators | type |
|---|---|---|
| `wallet_id` | `eq` `neq` `in` | UUID |
| `chain_id` | `eq` `neq` `in` | UUID |
| `amount` | `eq` `gte` `lte` `gt` `lt` | decimal |
| `currency` | `eq` `neq` `in` | string |
| `name` | `eq` `neq` `in` `contains` `icontains` | string |
| `category` | `eq` `neq` `in` `contains` `icontains` | string |
| `type` | `eq` `neq` `in` | string |
| `origin` | `eq` `neq` `in` | string |
| `created_at` | `gte` `lte` `gt` `lt` | datetime |
| `occurred_at` | `gte` `lte` `gt` `lt` | datetime — **currently identical to `created_at`**, see §6.2 |

**`POST /wallets/search`** — `name`, `currency`, `balance`, `created_at`, the
documented set in full.

**`POST /webhooks/search`** — `title`, `url`, `enabled`, `created_at`. Note
`enabled`, not `is_active` (§6.11).

`chain_id` being filterable is what makes §6.2's "re-read a chain by filtering
search on `chain_id`" work. Values are the ES-indexed ones: `type` is
`expense` / `income`, `origin` is `manual` / `scanned` / `automation`.

### 10.3 No `order` param anywhere

Sort order is fixed per collection and there is no way to ask for another one.

| collection | order |
|---|---|
| transactions | `created_at DESC, chain_sort ASC, id DESC` — chained legs group together, unchained rows sort last within their timestamp |
| wallets | `favorite DESC, created_at DESC, id DESC` |
| actions | `severity DESC, created_at DESC, id DESC` |
| everything else | `created_at DESC, id DESC` |

The leading key on wallets is applied **after** filtering, so a favourite that
does not match a search filter is absent like any other non-match.

### 10.4 `meta.cached`

Present on reads served by the read side. **Reads answered by the write-side
fallback always report `cached: false`.** Absent entirely on `GET /currencies`,
`GET /assistant/messages` and `GET /webhooks/{id}/deliveries`.

---

## 11. Summary of what has to be decided or built client-side

Ordered by how loudly it fails.

**Fails immediately, on the first call**
- `POST /assistant/messages` → 404. It is a WebSocket (§8).
- The three `/metrics/*` paths → 404. One endpoint with boolean params (§6.6).
- `new WebSocket()` against `/chat/advice` → 401 at the gateway, no
  client-side fix (§8).
- Native `EventSource` against `/notifications/stream` → 401. Use a
  fetch-based SSE client that can set `Authorization` (§8).
- Wallet detail's `last_month` → the key is `period` and takes a param (§6.3).
- `is_active` on webhooks → the field is `enabled`; `event_type` on
  subscriptions → the field is `event` (§6.11).
- `withCredentials: true` → CORS failure (§3.3).

**Returns 200 and is silently wrong**
- Money parsed to a float loses cents (§6.1).
- Summing `money.amount` across wallets counts an unspent credit line as the
  user's money (§6.3).
- `savings_rate: null` formatted as `0%` claims the user saved nothing when
  there was nothing to save (§6.6).
- A missing `unsafeMetadata` claim silently gives every user USD/UTC/en (§3.4).
- A per-request `Idempotency-Key` double-posts on retry (§3.1).
- Routing on `error.code` for a search 507 shows a crash banner instead of a
  retry — the code is `internal_error` (§4.4).
- `PATCH` with `new_amount` or `new_name` succeeds and changes nothing
  (§9).

**Transient, must be coded around**
- Spurious 404 on `/accounts`, `/accounts/{id}` and `/metrics` after any write
  (§4.3). **Retry, do not cache, do not render "not found".**
- `507` on the three searches after a write (§4.4). Retry shortly.
- `cursor_mismatch` on a filtered page 2 of notifications or webhooks (§4.5).
  Restart from page 1.
- A short HTTP timeout aborts the staleness reroute (§4.1).
- A transaction read immediately after creation shows `postings: []` (§6.2), and
  the ledger is not covered by `Read-At-Least` (§6.5).

**Not wired yet — build the UI, expect no data**
- The action queue is empty: nothing raises time-triggered actions (§6.7).
- The assistant reply is canned, though `refs` are real (§8).
- `goal.reached` is not in the event-type catalog (§6.11).
- `icon` on goal history is always `""` (§6.4).
- `occurred_at` filters, but returns exactly what `created_at` returns and is
  on no response body (§6.2). Holding it out of the plan is correct.
