# Where the backend differs from API_TARGET.md

Written for the frontend. Everything here is client-visible: a path that does not
exist, a field spelled differently, a status code the target does not mention, or
a behaviour a client has to code around. Internal decisions that a caller cannot
observe are deliberately not listed.

Current as of Phase 0 of [API_IMPLEMENTATION.md](./API_IMPLEMENTATION.md). The
conventions (envelope, cursors, money strings, timestamps, idempotency, filter
grammar, rate limits, `Read-At-Least`) are implemented as documented — the
differences below are on top of that.

## What exists today

Only four slices are live. Every path below is under `/api/v1` and takes a bearer
token like the target says.

| implemented                                                                                                 | notes                          |
|-------------------------------------------------------------------------------------------------------------|--------------------------------|
| `GET /wallets`, `GET /wallets/{id}`                                                                         | shape differs, see below       |
| `POST /wallets`, `PATCH /wallets/{id}`, `PUT /wallets/{id}`, `DELETE /wallets/{id}`                         | `PUT` is not in the target     |
| `POST /wallets/search`                                                                                      | —                              |
| `GET /transactions`, `GET /transactions/{id}`                                                               | shape differs, see below       |
| `POST /transactions`, `PATCH /transactions/{id}`, `DELETE /transactions/{id}`                               | bodies differ, see below       |
| `POST /transactions/search`                                                                                 | —                              |
| `GET /notifications`, `GET /notifications/{id}`                                                             | shape differs, see below       |
| `POST /notifications/{id}/ack`, `POST /notifications/ack`, `DELETE /notifications/{id}`                     | last two are not in the target |
| `GET /notifications/stream`                                                                                 | SSE, moved here from `/events` |
| `GET /webhooks`, `GET /webhooks/{id}`, `POST /webhooks`, `PATCH /webhooks/{id}`, `DELETE /webhooks/{id}`    | —                              |
| `POST /webhooks/{id}/secret`                                                                                | —                              |
| `GET /webhooks/{id}/events`, `POST /webhooks/{id}/events`, `DELETE /webhooks/{id}/events/{subscription-id}` | shape differs                  |
| `POST /webhooks/search`                                                                                     | not in the target              |

Not built yet. A request to any of these gets a plain 404 with NO error envelope —
nothing routes them, so no handler shapes the failure:

- the whole **Accounts**, **Goals**, **Currencies**, **Metrics**, **Actions**,
  **Automations** and **Assistant** slices;
- `POST /transactions/chains` and `DELETE /transactions/chains/{chain-id}`;
- `GET /notifications/count` — the bell badge has to come from
  `GET /notifications?...` for now;
- `GET /webhooks/event-types` — the event vocabulary is not served anywhere, so
  it has to be hardcoded client-side for the moment;
- `GET /webhooks/{id}/deliveries`.

## Resource shapes

### Transactions
- The money field is spelled **`amount` + `currency` as two flat siblings**, not
  a nested object. The target's examples nest it under `money`; its Conventions
  section says the field is called `amount`. Neither spelling is what we emit
  today: `{"amount": "90", "currency": "JPY"}` at the top level of the resource.
  The string itself already follows the Money Shape rules (canonical decimal at
  the currency's scale);
- Fields the target has and we do not emit: `name`, `type`, `origin`,
  `category`, `chain_id`, `evidence`, and the embedded `wallet: {id, name}`
  object on list items;
- Fields we emit that the target does not have: `wallet_id` (a plain id instead
  of the embedded wallet object), `occurred_at` (when the money moved, distinct
  from `created_at`);
- On the WRITE side only (`POST` / `PATCH` / `DELETE` responses) the transaction
  carries an embedded `wallet` object plus `cancels_other` / `adjusts_other` —
  ids of the ledger rows an edit or a delete appended. Reads never carry those;
- `GET /transactions/{id}` returns the same fields as a list item. No `postings`,
  no `analysis`, no `history` — those belong to the unbuilt Accounts slice.

### Wallets
- The balance is under **`balance`**, not `money`: `{"balance": {"amount":
  "50.00", "currency": "RUB"}}`. It IS a nested money object, unlike the
  transaction amount;
- Fields the target has and we do not emit: `currency` as a top-level field
  (it is only inside `balance`), `category`, `favorite`, `color`,
  `zero_balance`;
- Because `favorite` does not exist, wallets are ordered `created_at DESC, id
  DESC` — favourites do NOT lead the list yet;
- `GET /wallets/{id}` returns the same fields as a list item. No `last_month`,
  no `recent`.

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

## Request bodies

- `POST /transactions` takes `{source_wallet_id, amount}` — not `wallet_id`, and
  none of `name` / `currency` / `type` / `origin` / `category` / `evidence`. The
  currency comes from the wallet. `Idempotency-Key` is required, as documented;
- `PATCH /transactions/{id}` takes `{new_amount}` and adjusts the AMOUNT. The
  target's PATCH edits metadata (`name`, `category`, `evidence`) and never
  touches money. This is the largest single divergence in the slice: the same
  verb and path mean different things;
- `PATCH /wallets/{id}` takes `{new_name}` only — not `name`, and none of
  `favorite` / `category` / `zero_balance` / `color`;
- `PUT /wallets/{id}` exists (not in the target) and takes `{name, currency}`.
  Sending a different currency than the wallet was created with fails with 422;
- `POST /wallets` takes `{name, currency}` — no `color`, `opening_balance`,
  `zero_balance` or `category`;
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
- **`: heartbeat` comment lines are sent as documented**, so an idle stream is
  still distinguishable from a dead one.
