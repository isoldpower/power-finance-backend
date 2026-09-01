# Where the backend differs from API_TARGET.md

Written for the frontend. Everything here is client-visible: a path that does not
exist, a field spelled differently, a status code the target does not mention, or
a behaviour a client has to code around. Internal decisions that a caller cannot
observe are deliberately not listed.

Current as of Phase 5 of [API_IMPLEMENTATION.md](./API_IMPLEMENTATION.md). The
conventions (envelope, cursors, money strings, timestamps, idempotency, filter
grammar, rate limits, `Read-At-Least`) are implemented as documented — the
differences below are on top of that.

## What exists today

Every path below is under `/api/v1` and takes a bearer token like the target
says.

| implemented                                                                                                 | notes                          |
|-------------------------------------------------------------------------------------------------------------|--------------------------------|
| `GET /wallets`, `GET /wallets/{id}`                                                                         | detail takes `?period=`        |
| `POST /wallets`, `PATCH /wallets/{id}`, `PUT /wallets/{id}`, `DELETE /wallets/{id}`                         | `PUT` is not in the target     |
| `POST /wallets/search`                                                                                      | favourites lead the results    |
| `GET /transactions`, `GET /transactions/{id}`                                                               | detail carries `postings`      |
| `POST /transactions`, `PATCH /transactions/{id}`, `DELETE /transactions/{id}`                               | `PATCH` is metadata-only       |
| `POST /transactions/{id}/adjust`                                                                            | not in the target; see below   |
| `POST /transactions/chains`, `DELETE /transactions/chains/{chain-id}`                                       | transfers; see below           |
| `POST /transactions/search`                                                                                 | —                              |
| `GET /notifications`, `GET /notifications/{id}`                                                             | shape differs, see below       |
| `POST /notifications/{id}/ack`, `POST /notifications/ack`, `DELETE /notifications/{id}`                     | last two are not in the target |
| `GET /notifications/stream`                                                                                 | SSE, moved here from `/events` |
| `GET /webhooks`, `GET /webhooks/{id}`, `POST /webhooks`, `PATCH /webhooks/{id}`, `DELETE /webhooks/{id}`    | —                              |
| `POST /webhooks/{id}/secret`                                                                                | —                              |
| `GET /webhooks/{id}/events`, `POST /webhooks/{id}/events`, `DELETE /webhooks/{id}/events/{subscription-id}` | shape differs                  |
| `POST /webhooks/search`                                                                                     | not in the target              |
| `GET /currencies`                                                                                           | as the target describes it     |
| `GET /currencies/rates/{currency-code}`                                                                     | see below                      |
| `GET /currencies/convert`                                                                                   | as the target describes it     |
| `GET /goals`, `GET /goals/{id}`, `POST /goals`, `PATCH /goals/{id}`, `DELETE /goals/{id}`                   | detail embeds `history`        |
| `GET /accounts`                                                                                             | `group`/`lowbar`/`currency`    |
| `GET /accounts/{account-id}`                                                                                | detail embeds `history`        |

Not built yet. A request to any of these gets a plain 404 with NO error envelope —
nothing routes them, so no handler shapes the failure:

- the whole **Metrics**, **Actions**, **Automations** and **Assistant** slices;
- `GET /notifications/count` — the bell badge has to come from
  `GET /notifications?...` for now;
- `GET /webhooks/event-types` — the event vocabulary is not served anywhere, so
  it has to be hardcoded client-side for the moment;
- `GET /webhooks/{id}/deliveries`.

## Resource shapes

### Transactions
Transactions match the target preview shape. Two things are worth reading twice:
what a "transaction" actually is underneath, and where amount adjustments went.

- **A transaction is not a ledger row.** It is a mutable record — `name`,
  `category`, `evidence`, `origin`, `chain_id` — that OWNS one or more immutable
  money flows in the ledger. Creating one appends a flow; adjusting appends the
  difference; cancelling appends an inverse. Nothing ever rewrites a flow, which
  is why `PATCH` can be guaranteed never to touch money: the endpoint has no
  reach into the place money lives;
- **`money.amount` is always a positive magnitude and `type` carries the
  direction.** Internally the flows are signed and `type` is read off that sign,
  so the two cannot drift apart — there is no stored `type` to disagree with the
  money. `expense` is negative, `income` positive;
- **a cancelled transaction still reports the amount it was FOR.** `DELETE`
  echoes that figure back beside `deleted_at`, and so does detail. The wallet
  balance is the separate question, and it does return to where it stood;
- cancelled transactions leave `GET /transactions` and `POST /transactions/search`
  but still resolve by id. There is no `include_deleted` flag;
- **`occurred_at` is ours, not the target's.** It records when the money moved,
  as distinct from when the row was written, and it is filterable on
  `POST /transactions/search`. The target orders and reports on `created_at`
  alone, and so do we — `occurred_at` is additive;
- `GET /transactions/{id}` returns `postings: []` and `analysis: null` rather
  than omitting them, so a client never has to branch on the keys existing. Both
  are filled by the Accounts slice, which dispatches AFTER the write returns —
  so a transaction read immediately after creating it will legitimately show an
  empty ledger for a moment. `evidence` is real and returns `{"url": ...}` or
  null;
- ordering is `created_at DESC, chain_id ASC NULLS LAST, id DESC` exactly as
  documented. Chain members share a commit timestamp, so a transfer's legs arrive
  contiguously — though they may still straddle a page boundary;

#### Correcting an amount: POST /transactions/{id}/adjust
`PATCH /transactions/{id}` is metadata-only, per the target. Correcting an
**amount** is a different operation and has its own endpoint:

```
POST /api/v1/transactions/{id}/adjust
{ "amount": "70.00" }
```

- `amount` is the new **TOTAL**, not a delta. A user correcting a receipt types
  the right figure, not the difference from the wrong one;
- it stays a positive magnitude. Direction comes from the transaction's existing
  `type` and **cannot be changed here** — an expense stays an expense. Something
  that needs to become an income is a different operation, so cancel it and
  create the one you meant;
- the response is the preview shape with the new folded amount. The transaction
  keeps its `id`, its `created_at`, and its place in the feed;
- because the amount is absolute rather than incremental, re-sending the same
  request is a no-op. A retry cannot double-count;
- 409 if the transaction is already cancelled.

**The original is never rewritten and never cancelled.** The difference is
appended to the ledger as an adjusting flow linked back to the opening one, and
the transaction's amount becomes the new fold. Correcting 50.00 to 70.00 leaves
the 50.00 flow in place and adds a −20.00 beside it; the wallet balance moves by
20.00, not by 70.00. Corrections compose — adjust twice and there are three
flows and one transaction.

That is the whole reason to adjust rather than cancel-and-recreate: the audit
trail survives, and so does every reference to the transaction's id.

**Ahead of the target.** The specification reassigns `PATCH` to metadata and
defers adjustment transactions to a later revision, so it names no path for this.
Additive under the versioning rules, so it is legal inside v1 — but expect the
path or body to be renamed when the specification chooses one. `PATCH` still
ignores an unknown `new_amount` key rather than rejecting it, so a client on the
old spelling changes nothing and fails silently; move it to this endpoint.

#### Chains
- `POST /transactions/chains` is how transfers are expressed: an `expense` on one
  wallet and an `income` on another, committed atomically. `after` references
  `temporary_id`s in the same request and is a DEPENDENCY, not a sequence
  number — entries with no dependency commit in the order they were written;
- every leg of a chain shares one `created_at`. That is what makes the ordering
  keep them together;
- **the chain response's `meta.transactions` cursor never points anywhere.** The
  target specifies the pagination triple, so it is emitted, but a chain holds at
  most 100 entries and all of them are in the response — `next_cursor` and
  `prev_cursor` are always null. Do not build a paging loop against it. There is
  no endpoint that reads a chain by id; to re-read one, filter
  `POST /transactions/search` on `chain_id`;
- a failure anywhere rolls the whole chain back and no `chain_id` is issued.
  `error.details[].field` points at the offending entry by index, e.g.
  `transactions[1].after`;
- `DELETE /transactions/chains/{chain-id}` cancels every leg the same way a
  single DELETE does. Repeating it returns 200 with the same body;

### Wallets
Wallets match the target shape. The one thing worth reading twice is what
`zero_balance` means.

- **`zero_balance` is a credit datum, not a floor.** It is the point at which
  the wallet holds nothing of the user's own money. The balance MAY go below it,
  and below it the user owes `zero_balance - balance`. What the user actually
  owns is `balance - zero_balance`: a fresh credit card with a 100 limit opens
  at balance 100 and owns 0; spend 30 and it owns -30. An ordinary cash wallet
  has `zero_balance` 0, so it owns its whole balance;
- **`money.amount` is the SPENDABLE balance, not the owned figure.** The target
  carries `money` and `zero_balance` side by side precisely so a client can
  derive the difference itself. Nothing hides the credit line;
- when Metrics land, net worth will sum `balance - zero_balance` and the drawn
  portion of a credit line will be a liability. Do not build a client-side net
  worth that adds `money.amount` across wallets — an unspent credit line is not
  the user's money;
- `opening_balance` is POST-only. It is never echoed back in any response,
  because it is not stored on the wallet: it is realised as a real opening
  TRANSACTION at creation, which is what moves the balance. Omitting it opens
  the wallet on its datum (`opening_balance` defaults to `zero_balance`), owning
  and owing nothing. Expect that opening entry to appear in
  `GET /transactions` — until Phase 3 it has no `name` or `type` to tell it
  apart by, only its timestamp;
- wallets are ordered `favorite DESC, created_at DESC, id DESC`. The leading key
  is applied AFTER filtering, so a favourite that does not match a
  `POST /wallets/search` filter is absent like any other non-match;
- **DELETE closes a wallet only when `balance == zero_balance`** — settled in
  both directions. Money still in it and debt still owed on it both answer 409
  `wallet_not_empty`. Move the balance to its datum with `POST /transactions`
  first, then retry. Closing an already-closed wallet is 200 with the same body,
  and stays 200 even if the balance later drifts;
- a closed wallet leaves lists and search but **still resolves by id**. There is
  no `include_deleted` flag anywhere;
- **`GET /wallets/{id}` emits `period`, not the target's `last_month`, and takes
  a `?period=` query param.** The target hardcodes the window to the previous
  calendar month and gives wallet detail no way to ask for anything else, which
  forces a client that wants any other range onto `POST /transactions/search`
  plus client-side aggregation. We take `period=last_week|last_month|last_year|all_time`,
  default `last_month`, and renamed the response key to match — a field called
  `last_month` holding nineteen months would be actively misleading;
- every window except `all_time` is a **CALENDAR** window, not a rolling count of
  days: `last_month` on the 3rd is the whole of the previous month, not the
  preceding 30 days. Windows are half-open, so consecutive ones tile without
  double-counting the boundary instant. `all_time` genuinely drops both bounds
  rather than reaching for an old epoch;
- boundaries are resolved in the caller's `X-User-Timezone`, so two clients in
  different zones can legitimately see different figures for the same wallet and
  the same `period`. That is the one thing the timezone preference decides;
- `period.inflow` / `period.outflow` are both positive magnitudes in the
  WALLET's currency — nothing is converted, this is wallet detail, not Metrics;
- the window is echoed in `meta.period`. An unknown value is **422
  `validation_failed`** with `details[].field: "period"`, not a silent fall back
  to the default: answering about a different window than the one asked for is
  worse than refusing;
- `period` is never cached even when `meta.cached` is `true` — that flag reports
  on the wallet body, which is the part actually served twice;
- `GET /wallets/{id}` embeds `recent`: the wallet's own transaction feed, in the
  SAME preview shape and the same order as `GET /transactions`, paginated through
  the endpoint's `limit`/`cursor` and reported under `meta.recent`. Cancelled
  transactions are excluded, as everywhere else. Like `last_month`, it is
  computed per request and never cached;
- `PUT /wallets/{id}` is not in the target. It replaces the whole editable
  representation, so an omitted field resets to its default — unlike `PATCH`,
  where an omitted field is left alone.

### Goals
- Goals exist and match the target shape: `id`, `name`, `url` (always null),
  `currency`, `finish_at`, the three structural timestamps, `target` and
  `progress` as money objects;
- **`progress` is derived and never writable.** It is folded from the
  transactions touching the goal, exactly as a wallet's balance is. `PATCH`
  accepts a `progress` key and discards it rather than rejecting it;
- **`currency` is fixed at creation** and is not accepted by `PATCH`. Both
  `target` and `progress` are denominated in it, so letting it move would
  silently restate both;
- **a goal id is accepted anywhere `wallet_id` is.** Funding a goal is an
  ordinary `POST /transactions/chains` transfer — expense on a wallet, income on
  the goal — and draining it is the same chain reversed. There is no contribution
  endpoint;
- a transaction that moves money in a goal still renders it under the key
  **`wallet`**. That is what the target specifies; clients treat the two
  interchangeably and the container's kind is not part of the transaction shape;
- `DELETE /goals/{id}` refuses a non-zero `progress` with 409 `goal_not_empty`.
  Posting to a CLOSED goal fails with 409 **`wallet_closed`** — the same code the
  target defines for a soft-deleted target wallet, deliberately not a new one;
- `GET /goals/{id}` embeds `history`: one entry per transaction touching the
  goal, in the target's entry shape (`title`, `debit`, `created_at`,
  `source_transaction`, `icon`, `money`), paginated under `meta.history`.
  `debit` is true when money moved IN. `icon` is always `""` — nothing assigns
  one yet;
- **history entries carry an `id`.** The target's examples omit it; a
  keyset-paginated collection needs a stable anchor;
- there is **no `POST /goals/search`**, matching the target. That is a decision,
  not a gap.

### Accounts
- Accounts are **read-only**, as the target says. Nothing creates, edits or
  deletes one: they are derived by the backend from your transactions;
- **the balance is a `money` object, not a bare decimal.** Every account is
  denominated in a single BOOK currency (`USD` today) — postings are converted
  into it before they are summed — so `money.currency` is the book currency and
  NOT the currency of the transactions behind it. A history entry, by contrast,
  carries the currency of its own transaction, so the two legitimately differ
  inside one response;
- **the account shape carries `created_at` and `updated_at`.** The target's
  example has no timestamps at all, yet sorts on `created_at`; exposing the sort
  key is the additive half of that fix. There is no `deleted_at` — an account is
  never deleted;
- ordering is `created_at DESC, id DESC`. **`group` filters and does not order**
  — assets do not lead liabilities;
- **`lowbar` compares MAGNITUDES, not signed balances.** A liability's balance is
  negative, so a signed comparison would empty that group the moment you set any
  threshold. `?lowbar=1.00` hides everything smaller than 1.00 in either
  direction;
- `lowbar` is read in `currency` (default `USD`) and converted into each
  account's book currency before it compares. An unknown `currency` is 422
  `unsupported_currency`; a `lowbar` finer than that currency's scale is 422
  `amount_precision`. `meta` echoes both back so you can confirm what was
  applied. A `lowbar` of `0` — the default — excludes nothing and reaches no rate
  feed, so it can never fail with `rate_unavailable`;
- **`meta.groups` ignores `group` but honours `lowbar`.** The target only
  specifies the first. Ignoring the threshold too would make a tab advertise a
  count that selecting it does not produce. Every group is present, including
  ones holding nothing;
- an unknown `group` is 422 `validation_failed`. The accepted values are `all`
  (default), `assets`, `liabilities`, `equity`;
- `GET /accounts/{account-id}` embeds `history` — the postings dispatched into
  the account, in the target's entry shape, paginated under `meta.history`.
  `debit` is true when the leg debits the account. **Entries carry an `id`**, for
  the same reason goal history does;
- there is **no `GET /accounts/{account-id}/postings`.** An earlier build served
  the postings as their own collection; the detail endpoint the target specifies
  replaced it. Page the history through the detail's `limit` and `cursor`;
- `analysis.balanced` on a transaction is a **diagnostic, never an error**. It is
  most often `false` when the two legs landed in different currencies;
- both endpoints honour `Read-At-Least`, but **the ledger is not reachable
  through it.** That header tracks write-service's outbox; ai-service dispatches
  from its own sequence, after your write has already returned. So a
  `Read-At-Least` satisfied for the transaction says nothing about its postings
  having landed — poll rather than expecting read-your-writes on the ledger;

### Notifications
- The fields are **`short`, `message`, `is_read`** — not `title`, `body`,
  `acknowledged_at`. `is_read` is a boolean, so there is no timestamp for when
  it was acknowledged;
- `severity` and `subject` do not exist. Nothing to branch on for urgency and
  nothing to deep-link to;
- `payload` is an extra free-form JSON object we emit and the target does not
  document;
- `GET /notifications` takes **`only_unread=true`**, not the target's
  `acknowledged` / `severity` params;
- `POST /notifications/{id}/ack` returns `{"acknowledged_ids": [...]}`, not the
  updated notification. Same for the batch endpoint. A client that needs the
  updated resource has to re-read it.

### Currencies
- `symbol` is `""` for any code we have no established symbol for. Fall back to
  the `code` rather than rendering an empty span. Every one of the 34 codes we
  currently serve has one;
- the table is 34 codes, not the target's example count of 40. It is whatever
  `GET /currencies` returns — do not hardcode a list;
- **`decimals` is the authority for rendering every amount in that currency.**
  Fetch this endpoint before anything that formats money, exactly as the target
  says: JPY amounts have no fraction digits, USD has two;
- rates are quoted against a base that must be one of these codes. A code we
  serve here is not automatically a code the rate FEED quotes — see below.

### Webhooks
- The enable switch is **`is_active`**, not `enabled`, on both the resource and
  the create/update bodies;
- Webhook resources carry `deleted_at: null`. The target says webhooks have no
  `deleted_at` at all because they are hard-deleted — the key is present here
  purely for uniformity and is always null;
- Subscriptions spell the event type **`event_type`**, not `event`, and add
  `is_active`;
- `GET /webhooks/{id}/events` is NOT paginated: it returns everything with
  `meta.limit: null` and both cursors null. The target paginates it.

## Currencies and rates

- **`GET /currencies/rates/{currency-code}` takes `target` in either spelling.**
  `?target=RUB&target=EUR` and `?target=RUB,EUR` mean the same thing. `meta.target`
  echoes the normalised, upper-cased list, or `null` when you asked for the whole
  map;
- **An unknown code in `target` is a 422, not a gap in the map.** Sending
  `?target=RUB,XYZ` fails the whole request with `unsupported_currency` rather
  than returning RUB alone. That is deliberate: a silently missing entry cannot
  be told apart from a currency the feed does not quote;
- **A code in `GET /currencies` is not a promise of a rate.** The currency table
  and the rate feed are different sources. A code we list but the feed does not
  quote answers `409 rate_unavailable`, and retrying later is the correct
  response — it is not a client error. `422 unsupported_currency` is the one that
  means "fix the code you sent";
- **Rates are never stale-but-served.** If the feed has not published inside its
  freshness window, both rate endpoints answer `409 rate_unavailable` rather than
  handing back an old number. Show the user that the rate is unavailable rather
  than a figure with no timestamp attached;
- **The upstream feed publishes once a day.** `meta.fetched_at` is the FEED's
  publication time, not when the response was built, so it will routinely be
  hours old. Do not treat a `fetched_at` in the past as an error, and do not poll
  these endpoints faster than the data changes;
- **`rate` is not money and `to` is authoritative.** `GET /currencies/convert`
  returns `from` and `to` as money objects at their own scales, plus `rate` as a
  bare unpadded string with up to 12 fraction digits and no currency. Render
  `to`; multiplying `rate` client-side can land on a different last digit,
  because the server rounds once, half-up, at the TARGET currency's scale;
- **`amount` is validated against `from_code`'s scale, not `to_code`'s.**
  `?from_code=USD&amount=100.005` fails with 422 / `amount_precision`;
  `?from_code=JPY&amount=10.5` fails the same way, since JPY has no minor unit;
- **`GET /currencies` is not paginated.** `meta.limit` and both cursors are
  `null`, `meta.total` counts everything returned, and there is no `meta.cached`
  key on it at all;
- **None of the three endpoints honours `Read-At-Least`.** They carry no
  user-owned data, so they can never answer 507 and never need the gateway's
  fallback re-route.

## Request bodies

- `POST /transactions` takes `{name, wallet_id, currency, amount, type,
  origin?, category?, evidence?}` as the target says. `amount` is a positive
  magnitude — `type` states the direction. `Idempotency-Key` is required;
- `PATCH /transactions/{id}` takes `{name?, category?, evidence?}` and nothing
  else. `new_amount` is gone and sending it changes nothing — corrections go to
  `POST /transactions/{id}/adjust`, described above;
- `POST /transactions/{id}/adjust` takes `{amount}`, the new total as a positive
  magnitude. Not in the target;
- `POST /transactions/chains` takes `{transactions: [...]}` where each entry is a
  `POST /transactions` body plus `temporary_id` and `after`. At most 100 entries;
  more is 422 `chain_too_long`. One `Idempotency-Key` covers the whole chain;
- `PATCH /wallets/{id}` takes `{name?, favorite?, category?, zero_balance?,
  color?}` as the target says. Every field is optional and an omitted one is
  left alone, so `{}` is a legal no-op. It renamed the field from `new_name` to
  `name` in Phase 2 — a client still sending `new_name` now silently changes
  nothing rather than failing;
- `PUT /wallets/{id}` exists (not in the target) and takes `{name, currency}`
  plus the same optional metadata as `PATCH`. Unlike `PATCH`, an omitted field
  RESETS to its default, since PUT replaces the representation. Sending a
  different currency than the wallet was created with fails with 422;
- `POST /wallets` takes `{name, currency, category?, color?, zero_balance?,
  opening_balance?}`. `color` is validated as a CSS hex colour
  (`#RGB` / `#RRGGBB` / `#RRGGBBAA`) — the target shows one but names no format;
- `zero_balance` and `opening_balance` are flat decimal strings validated
  against the wallet currency's scale, as the target describes;
- `POST /webhooks` takes `{title, url}`; `PATCH /webhooks/{id}` takes
  `{title?, url?}`. Neither accepts `enabled`;
- `POST /webhooks/{id}/events` takes `{event_type}`, not `{event}`.

## Behaviour

- **A stale `/search` can return 507.** `POST /{resource}/search` is the one read
  the gateway cannot transparently re-route when the read side is behind the
  caller's write version, because the write side has no search. The target says
  no error code covers staleness; in practice a search sent immediately after a
  write (with `Read-At-Least` in play) may answer `507` with an error envelope.
  Treat it as "retry shortly", not as a failure to show the user. Every other
  read is re-routed and never shows it;
- **Three error codes exist that the target's table does not list.** Clients must
  tolerate unknown codes anyway, but these are the ones we actually emit:
  `service_unavailable` (503, a dependency is down — retrying is correct),
  `insufficient_funds` (409, the wallet is short), `conflict` (409, a state
  conflict the contract names no specific code for). There is also one extra
  `details[].code`: `invalid`, for a field of the wrong shape, since the Detail
  Codes table has no generic member for that;
- **Filterable fields are narrower than documented.** `POST /transactions/search`
  accepts `wallet_id`, `amount`, `currency`, `created_at` and `occurred_at`
  (ours, not in the target). It does NOT yet accept `chain_id`, `name`,
  `category`, `type` or `origin` — those columns do not exist, and sending them
  fails with 422 / `filter_unknown_field`. `POST /wallets/search` accepts the
  documented set (`name`, `currency`, `balance`, `created_at`) in full;
- **No `order` param anywhere.** Every collection is `created_at DESC, id DESC`.
  Transactions do not group by `chain_id` and wallets do not lead with
  `favorite`, both because those columns do not exist yet;
- **`meta.cached` is present on reads served by the read side.** Reads answered
  by the write-side fallback always report `cached: false`;
- **Mutations carry `Idempotent-Replayed: true` as well as
  `meta.idempotent_replay`.** The header is a convenience; the meta key is the
  contract, as documented;
- **The SSE stream is a general event feed, not a notification feed.** It is
  wired to the user's outbox, so it emits EVERY domain event for that user —
  `TransactionCreated`, `WalletUpdated`, and so on — with the domain event name
  in `event:` and the raw outbox payload in `data:`. The target's
  `notification.created` / `notification.acknowledged` names and their
  notification-resource payloads do not exist. A client must ignore event names
  it does not recognise, and cannot treat `data:` as a notification resource;
- **The stream does not resume.** `id:` is the outbox event id, but
  `Last-Event-ID` is not read on reconnect and the consumer starts from the
  live end of the topic. Anything produced while disconnected is lost — refetch
  `GET /notifications` after every reconnect, which the target already
  recommends as the safe path;
- **The OpenAPI documents now generate cleanly**, at `/api/schema` on each
  service. If you generate a client from them, the response component names
  changed: a list item is `<Resource>Preview`, a detail item is
  `<Resource>Detail`, and a search hit is `<Resource>SearchResult` — previously
  every one of them was `<Resource>Response` and collided, so the generated
  types were wrong. Money is a single `Money` component everywhere, and auth is
  declared as one `clerkBearer` HTTP bearer scheme, which is what you already
  send;
- **`: heartbeat` comment lines are sent as documented**, so an idle stream is
  still distinguishable from a dead one.
