# Where the backend differs from API_TARGET.md

Written for the frontend. Everything here is client-visible: a path that does not
exist, a field spelled differently, a status code the target does not mention, or
a behaviour a client has to code around. Internal decisions that a caller cannot
observe are deliberately not listed.

Current as of Phase 11 of [API_IMPLEMENTATION.md](./API_IMPLEMENTATION.md). The
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
| `GET /notifications`, `GET /notifications/{id}`                                                             | `acknowledged`, `severity`     |
| `GET /notifications/count`                                                                                  | the bell badge                 |
| `POST /notifications/{id}/ack`, `POST /notifications/ack`, `DELETE /notifications/{id}`                     | last two are not in the target |
| `GET /notifications/stream`                                                                                 | SSE, moved here from `/events` |
| `GET /webhooks`, `GET /webhooks/{id}`, `POST /webhooks`, `PATCH /webhooks/{id}`, `DELETE /webhooks/{id}`    | —                              |
| `POST /webhooks/{id}/secret`                                                                                | —                              |
| `GET /webhooks/{id}/events`, `POST /webhooks/{id}/events`, `DELETE /webhooks/{id}/events/{subscription-id}` | not paginated                  |
| `GET /webhooks/event-types`                                                                                 | the subscription vocabulary    |
| `GET /webhooks/{id}/deliveries`                                                                             | `status`, `event`; see below   |
| `POST /webhooks/search`                                                                                     | not in the target              |
| `GET /currencies`                                                                                           | as the target describes it     |
| `GET /currencies/rates/{currency-code}`                                                                     | see below                      |
| `GET /currencies/convert`                                                                                   | as the target describes it     |
| `GET /goals`, `GET /goals/{id}`, `POST /goals`, `PATCH /goals/{id}`, `DELETE /goals/{id}`                   | detail embeds `history`        |
| `GET /accounts`                                                                                             | `group`/`lowbar`/`currency`    |
| `GET /accounts/{account-id}`                                                                                | detail embeds `history`        |
| `GET /metrics`                                                                                              | **replaces three paths**       |
| `GET /actions`                                                                                              | `status`, `source`, `severity` |
| `POST /actions/{action-id}/resolve`                                                                         | returns the answered action    |
| `GET /automations`, `GET /automations/{id}`                                                                 | `enabled` filter               |
| `POST /automations`, `PATCH /automations/{id}`, `DELETE /automations/{id}`                                  | rules run; see below           |

Everything in API_TARGET.md is now routed. The one path that does NOT exist is
`POST /assistant/messages` — see Assistant below for what replaces it.

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

### Metrics
**The target's three endpoints are one endpoint here.** `GET /metrics/balance`,
`GET /metrics/net-worth` and `GET /metrics/cash-flow` do not exist. Everything
they described is on:

```
GET /api/v1/metrics?balance=true&net-worth=true&cash-flow=true
```

The three sections read the same rows and differ only in how those rows are
folded, so splitting them across three paths bought three round trips, three
authentications, three cache entries and three scans of `read_transactions` for
one screen's worth of numbers. Merged, net worth's opening balance, its all-time
total and cash flow's two directional figures come out of a **single grouped
query**, and one rate lookup per currency serves the whole response instead of
one per section.

- each selector is an independent **boolean defaulting to `true`**, so a bare
  `GET /metrics` returns all three — the call this endpoint exists for. Accepted
  spellings are `true/false`, `1/0`, `yes/no`, `on/off`; anything else is 422
  against that selector's own name;
- **an excluded section comes back as `null`, not missing.** The three keys are
  always present, so you never branch on whether one exists;
- the JSON keys are `balance`, **`net_worth`** and **`cash_flow`** — snake_case
  like every other key in this API. The query params keep the target's
  hyphenated spelling (`net-worth`, `cash-flow`) because that is what its paths
  were called;
- dropping a section really does skip its work: `?balance=false` issues no query
  against the chart of accounts, and `?net-worth=false` buckets no series;
- `meta.sections` echoes which sections the response actually carries;
- selecting only one section costs two explicit `false` params. That is the
  deliberate trade — the common call is all three, and it is now free;
- asking for nothing (`?balance=false&net-worth=false&cash-flow=false`) is a
  200 with three nulls, not an error;

`meta` carries `since`, `points`, `sections` and `cached` on every response,
including when the section a param applies to was not requested.

Every figure is in your PREFERRED currency (Clerk
`unsafeMetadata.currency`, defaulting to `USD`). There is deliberately **no
`currency` query param** — a per-request override would be a second way to
choose the reporting currency and the two would disagree the moment one was
cached. A preference change is not an API write, so nothing invalidates on the
server: after changing it, refetch.

- the response carries `meta.cached`, and a cached response may still be
  denominated in the currency you preferred a minute ago;
- an amount whose denomination the backend never learned is counted at face
  value rather than dropped, so a figure is never silently understated;

**The `balance` section**
- amounts are **normal-balance positive**: a liability owing 20 is `"20.00"`,
  not `"-20.00"`. The identity to check is `assets == liabilities + equity`;
- `balanced` is false if that identity fails **or** if any transaction was
  posted with legs that disagreed — most often a cross-currency posting. Both
  are diagnostics; an unbalanced sheet is still a 200;
- **`comments` is a string or null**, not an array. The target names it plurally
  but shows `null` rather than `[]`; reasons are joined into one string so you
  never branch on an array;

**The `net_worth` section**
- net worth is the running total of every non-cancelled transaction against your
  containers. **A transfer does not change it** — both legs are yours and they
  cancel. It is computed from transactions, not from the ledger, so it is
  correct before the accounts slice has dispatched anything;
- `since` bounds `net_worth`'s series and `cash_flow`. It does NOT bound
  `balance`, which is a snapshot of the chart as it stands;
- `since` selects the WINDOW, not the balance: money held before it still counts
  toward `money`. What `since` bounds is `net_diff` and the `series`;
- with no `since`, the window opens at your **first transaction** rather than
  padding the front of the series with zeroes;
- `series` has exactly `points` entries and is **not paginated** — no cursors in
  `meta`. Each point is the running total at the **end** of its slice, so the
  last point equals `money`;
- `points` defaults to 10 and is **clamped** to 1..100, not rejected;
  `meta.points` reports what was applied. A non-integer is 422 against the field
  `points`;
- **`net_diff.percentage` is null when the window opened at zero.** Any gain from
  nothing is infinite growth. `direction` still tells you which way it went, and
  `flat` is a real value;

**The `cash_flow` section**
- **transfers are excluded from both halves.** A chain moves money between two
  containers you already own; counting it would report the same money as income
  and as spending. It nets out of `total_net` either way, but it would inflate
  `inflow` and `outflow` and make `savings_rate` meaningless. The target does not
  specify this;
- `inflow` and `outflow` are both **positive magnitudes**;
- **`savings_rate` is `total_net / inflow * 100`** — a bare number, not money.
  The target's example shows `15` for inflow 15 / outflow 10, which is `inflow`
  repeated rather than any rate; the same figures return `75.0` here;
- `savings_rate` is **null when nothing came in**, not zero — a rate against no
  income is undefined, and zero would claim you saved nothing when there was
  nothing to save;

### Automations
Rules can be **authored, read, edited and deleted**, every validation the
target describes happens at CREATE time, and the engine runs them. What running
them actually means is at the end of this section — three of its rules are
things the target left open.

- `trigger.filter_body` is the SAME filter tree the `/search` endpoints take,
  checked against the policy of the trigger's **subject**: an `event` trigger
  against transactions, a `schedule` trigger against wallets. Failures carry the
  same `filter_*` detail codes search does, with a JSON path INTO the tree
  (`trigger.filter_body.and[1].or[0].operator`) so you can highlight the exact
  condition;
- **`filter_body: null` means "always".** An empty group (`{"and": []}`) is
  refused rather than meaning the same thing — two spellings of one idea is one
  too many;
- **requests supply ONE of `trigger.event` / `trigger.schedule`; responses carry
  both**, the inapplicable one `null`, so you read `trigger.schedule` without
  guarding. Sending the one that does not match the declared `type` is 422
  `trigger_field_conflict`;
- **`effects` is a closed vocabulary and `params` must be exactly what each
  effect documents.** An unknown key is 422 `effect_params_invalid` rather than
  a silently ignored setting. `transfer` takes the ordinary money grammar, so
  `{"amount": 200.0}` is refused — send `"200.00"`;
- an effect that cannot apply to the trigger's subject is 422
  `effect_subject_mismatch` **at create time**, not silently at run time —
  `set_category` on a scheduled rule, for instance;
- `effects` needs at least one entry: a rule that matches and does nothing is
  never what was meant;
- **there is no `/toggle`.** Enabling is `PATCH {"enabled": false}` — setting a
  field, not flipping one, because a toggle is not idempotent;
- **`trigger` and `effects` are replaced WHOLE** when supplied, never merged.
  There is no way to say "change the third leaf" of a condition tree, so send
  the complete new one;
- `DELETE` is a **soft delete** returning the removed rule. It leaves
  `GET /automations` but still resolves by id. Nothing it already did is
  reverted;
- ordering is `created_at DESC, id DESC` — the REVERSE of evaluation order. The
  list shows newest first because that is how you think about your rules; the
  engine is specified to run oldest first so later rules override earlier ones;
- `enabled` is a TRISTATE filter: absent means both;
- `icon` is free-form with a client-side registry, never validated server-side;

#### What running a rule means
The target specifies evaluation order and says a failed run does not roll back.
It leaves three questions open that you can observe from the client, so they are
answered here.

- **an event rule fires ONCE per transaction, ever.** Editing a transaction a
  rule already saw does not run that rule again — otherwise fixing a typo in a
  name would repeat its `transfer`, and two rules setting the same category
  would flip it back and forth forever. A rule created AFTER a transaction never
  sees it either: rules are forward-only;
- **a scheduled rule fires once per wallet per period**, where the period is the
  calendar one — a date for `daily`, an **ISO week** (Monday-based) for
  `weekly`, a month for `monthly`. So a user with three wallets sees three runs
  a day from one daily rule, one per wallet, which is what "a scheduled rule
  scans wallets" means;
- **`runs` counts only runs that applied EVERY effect.** A run that failed
  partway keeps what it already did, exactly as the target says, but does not
  count — `runs` is what tells you a rule still works, so a half-run must not
  report as one. A rule that matched a thousand times and always failed reports
  `0`;

Three things a rule produces are recognisable:

- **`transfer` creates transactions with `origin: "automation"`.** This is a
  NEW value in the `origin` vocabulary — treat it the way the Client
  Obligations require, as an unknown-but-valid case if you switch on `origin`.
  It is server-authored: `POST /transactions` rejects it, because claiming it
  would be a way to make a transaction invisible to every rule. The engine
  ignores transactions carrying it, which is what stops a rule from firing on
  the money it just moved;
- **`raise_action` produces an action with `kind: "automation"`** and
  `source: "scheduler"`, grouped by the rule that raised it. A daily rule that
  keeps matching therefore bumps ONE action's `occurrences` rather than
  appending an action a day. Its `resolutions` are the backend's — an
  acknowledgement and a dismissal, neither of which `applies` — because a
  user-authored rule cannot define the choices offered to a user;
- **`notify` writes its own `body`**, naming the rule that fired. The rule
  supplies `severity` and `title` and nothing else; there is no template string
  anywhere in the API;

`runs` and `last_run_at` are projected from the engine, so they arrive on the
read side a moment after the run — the same eventual-consistency window as every
other counter here, and `X-Write-Version` does not cover them because no request
of yours caused the run.

### Actions
The queue matches the target shape. Two things are worth reading twice: what
orders it, and what happens when you answer.

- **the queue leads with urgency**: `severity DESC, created_at DESC, id DESC`.
  This is the one collection in the API that does not order purely by recency —
  it is a list to be worked through, not a feed to be read;
- **`status` defaults to `pending`.** Passing `resolved`, `dismissed` or
  `expired` shows those slices instead. `source` and `severity` are absent by
  default, meaning all. An unknown value for any of the three is 422 against
  that param's own name — the server will not quietly answer about a different
  slice than you asked for;
- **render one button per entry in `resolutions` and never switch on `kind`.**
  `kind` is an open vocabulary; use it to pick an icon and fall back to a
  generic one. Deriving labels or button counts from it reintroduces exactly the
  coupling this shape removes;
- `resolutions[].intent` is a rendering hint, not behaviour. You may style them
  all identically;
- **`money` is in the currency the action concerns**, not your reporting
  currency. This is not Metrics — nothing is converted. `null` when the action is
  not about an amount;
- `group_key` collapses recurring conditions onto one row: a daily check bumps
  `occurrences` and `last_seen_at` rather than appending an action per run.
  `null` means it does not recur, and `occurrences` is 1 for those, never 0;
- there is **no `/search` and no detail endpoint**, matching the target. The list
  row carries the entire resource;

**`POST /actions/{action-id}/resolve`**
- returns the answered action with **`resolutions` emptied**. A resolved action
  offers no further choices, and an empty array rather than a stale list is what
  stops you re-rendering buttons that no longer work;
- **`X-Write-Version` is present only when the chosen resolution had
  `applies: true`.** When it was false nothing outside the action changed, so
  there is nothing to send `Read-At-Least` against and the header is omitted
  entirely rather than sent with a value you cannot use;
- choosing the resolution the server designates as dismissal produces
  `status: "dismissed"`; every other choice produces `"resolved"`. Which one that
  is is not exposed — it is a server decision, and you render buttons either way;
- `resolution_id` must be one offered on THAT action; anything else is 422
  `unknown_resolution`, including an id valid on a different action;
- answering an already-answered, dismissed or **expired** action is 409
  `action_already_resolved`;
- a resolved action is **not** soft-deleted: `deleted_at` stays null and
  `status` carries the queue state;

**What produces actions.** Nothing does yet, in practice. The write path
(`RaiseActionCommand`), the recurring collapse and the expiry sweep are all
built and running, but no scheduled CHECK exists to raise time-triggered actions
— the target's example condition depends on subscriptions, which this system
does not model. The assistant does not raise them yet either. Expect an empty
queue until something starts filling it.

### Notifications
Notifications now match the target shape: `severity`, `title`, `body`,
`subject`, `acknowledged_at` and the three structural timestamps. The old
`short` / `message` / `is_read` fields and the free-form `payload` object are
**gone from the wire** — `only_unread` is gone with them.

- **`acknowledged_at` is a timestamp, not a boolean.** `null` means unread. It
  records when the user saw it, so it never moves: acknowledging twice keeps the
  first value, and so does a redelivered event;
- **`acknowledged` is a TRISTATE.** Absent means both, which is not the same
  request as `acknowledged=false`. `severity` filters to one of `info`,
  `warning`, `critical`; an unknown value is 422 against that param's own name;
- **`severity` does not reorder the feed.** Ordering is the global default,
  `created_at DESC, id DESC`. This is a feed to be read, not a queue to be
  worked through, so a `critical` from Tuesday does not outrank an `info` from
  this morning;
- **`subject` is `null` unless both halves are present.** A `{type, id}` with an
  empty id is not a deep link, so it is not sent as one;
- `payload` — the producer's own bag — is stored but never returned. What you
  deep-link to is `subject`;
- **both ack endpoints now return notification resources**, not
  `{"acknowledged_ids": [...]}`. Single ack returns the one notification; the
  batch returns every notification named in the request, in list shape;
- `POST /notifications/{id}/ack` is idempotent by nature and needs no
  `Idempotency-Key`. Re-acking is a **200 carrying the original
  `acknowledged_at`**, never a 409. There is no un-acknowledge;
- `POST /notifications/ack` (batch) and `DELETE /notifications/{id}` are not in
  the target. The batch takes an explicit list of ids — "acknowledge
  everything", filtered or not, is still an open item;

**`GET /notifications/count`** returns `{"unacknowledged", "total"}` with an
empty `meta`. It is deliberately uncached and reads both figures in one query.
The value goes stale the moment the stream delivers something: increment locally
on arrival rather than refetching per event.

**`GET /notifications/stream`** now emits the documented events rather than raw
internal frames:

- `notification.created` carries the FULL resource, identical to one element of
  `GET /notifications`, so you prepend it without a follow-up request;
- `notification.acknowledged` carries `{id, acknowledged_at}` only, and one
  frame is emitted **per notification** even when several were acknowledged
  together — a second device's batching is not your concern;
- the SSE `id:` is the **notification id**, not an internal event id;
- **the stream carries only these two events.** It used to relay every outbox
  frame for the user — wallet and transaction events included; those are gone.
  Nothing documented consumed them;
- **`Last-Event-ID` replays nothing.** The target allows resume to be best
  effort "bounded by server-side retention", and ours is zero: push-service is a
  stateless broadcast consumer that reads from the end of the topic and keeps no
  backlog. Reconnect by refetching `GET /notifications`, which the target already
  names as the recommended path in every case;
- heartbeat comments arrive every 15 seconds, inside the documented 30, and
  `X-Accel-Buffering: no` is set so no intermediary can buffer the stream into
  looking hung;

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
Endpoints and subscriptions now match the target's field names — this is a
BREAKING change from the previous release and every point below is new:

- **`is_active` is now `enabled`**, on the resource and on the create/update
  bodies. `POST /webhooks` and `PATCH /webhooks/{id}` accept it, so an endpoint
  can finally be paused without deleting it. `GET /webhooks?enabled=` filters on
  it, and like every other flag filter here it is a TRISTATE: absent means both;
- **`deleted_at` is gone from webhook resources.** Webhooks are hard-deleted and
  the key was always null; it is no longer sent at all;
- **Subscriptions spell the event type `event`**, not `event_type` — in the
  `POST /webhooks/{id}/events` body as well as in responses. `is_active`,
  `updated_at` and `deleted_at` are gone from the subscription shape; it is now
  exactly `{id, webhook_id, event, created_at}`;
- `GET /webhooks/{id}/events` is NOT paginated: it returns everything with
  `meta.limit: null` and both cursors null. The target paginates it;
- **`GET /webhooks/event-types` serves five event types, not the target's six.**
  `goal.reached` is absent: nothing publishes it yet, and advertising a
  subscription that would never fire is worse than a short catalog. The others —
  `transaction.created`, `transaction.updated`, `transaction.deleted`,
  `wallet.created`, `wallet.updated` — are all live. Adding one later is
  additive, which is exactly why this list is served rather than documented;
- **`POST /webhooks/search` filters on `enabled` too**, not `is_active`;
- **`GET /webhooks/{id}/deliveries` is answered by a different service**, so its
  `meta` has no `cached` key. Everything else matches: `status` and `event`
  filters, keyset `cursor`, `limit` capped at 100, the payload deliberately
  absent, and the log surviving its endpoint's deletion. `status` accepts the
  five documented values and a sixth is a 422; `next_attempt_at` and
  `last_error` are `null` on a finished delivery rather than blank.

### Assistant
**Sending a message is a WebSocket, not `POST /assistant/messages`.** That path
does not exist and never will in v1; a request to it gets a plain 404 with no
error envelope. Open `GET /api/v1/chat/advice` instead — the same socket that
was already there — and send `{"text": "..."}`.

The reply comes back as frames shaped `{"event": ..., "data": {...}}`, carrying
the target's own event names and in the target's order:

| event      | `data`                                                        |
|------------|----------------------------------------------------------------|
| `accepted` | `{user_message_id, message_id}` — both messages are persisted  |
| `delta`    | `{text}` — an increment. Concatenate in arrival order          |
| `message`  | the finished message, with `refs`. Replaces the accumulated text |
| `error`    | `{code, message, message_id}`. Terminal for the turn           |

Everything the target promises about that exchange holds: `accepted` arrives
before any generation so a client that drops immediately still knows both ids;
`delta` carries text only; the terminal `message` repeats the full text because
`refs` are not known until the end; and the reply is persisted whether or not
you are still listening, so a dropped connection means refetching
`GET /assistant/messages`, never re-sending.

What differs beyond the transport:

- **the socket stays open after a turn.** `error` is terminal for that reply,
  not for the connection — send another `{"text": ...}` and the conversation
  carries on. A frame no handler understands closes the socket with 1003;
- **`Idempotency-Key` is not supported here.** A WebSocket frame carries no
  headers. Send a message twice and you get two turns;
- **there is no stricter rate-limit tier on sending.** The gateway limits the
  handshake, not the frames;
- **`assistant_unavailable` is an `error` frame code, not a 503.** There is no
  HTTP response to put a status on;
- **the reply is canned.** No model is wired: the assistant answers
  `"Received message: {your text}"`, streamed as several deltas. `refs` are
  still real — any transaction or account id that appears in the reply and
  belongs to you comes back as a chip, so the citation path is live even though
  the wording is not;
- **`GET /assistant/messages` has no `meta.cached`.** It is not cached;
- **`GET /assistant/overview` carries `meta.cached`, but the cache is per
  server process**, not shared. Two requests seconds apart can both report
  `cached: false` if they land on different replicas;
- **`signals` are three fixed labels** — `Spend vs last month`, `Uncategorised`,
  `Recorded this month` — not the target's examples. `value` is preformatted
  display text exactly as documented and must not be parsed: it can read
  `+38%`, `no baseline yet`, `nothing yet` or `3 transactions`. The spend
  comparison is computed within a single currency and the months are calendar
  months in UTC, not in your timezone preference;
- **`prompts` adapt slightly** — you get a "still need a category" suggestion
  when you have uncategorised transactions, and a "record your first
  transaction" one when the ledger is empty.

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
  magnitude — `type` states the direction. `Idempotency-Key` is required.
  `origin` accepts `manual` and `scanned` only: responses can also carry
  `automation`, which is server-authored — see Automations;
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

- **A stale read can return a spurious 404 on three endpoints.** The gateway
  re-routes a stale read to the write side, and that now works for wallets,
  transactions, goals, notifications (list, detail AND count), webhooks,
  actions and automations. It does NOT work for `GET /accounts`,
  `GET /accounts/{account-id}` and `GET /metrics` — there is no write-side copy
  of those, so the reroute lands on a path that does not exist and you get a
  **404 with no error envelope** for a resource that is really there. It is
  transient: the projection catches up within moments of a write. Retry rather
  than treating it as a missing resource, and do not cache the 404;
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
  still distinguishable from a dead one;
- **Webhook deliveries are signed over `"{timestamp}.{body}"`, as the target's
  Signature section specifies**, and now carry `X-Webhook-Timestamp`. A receiver
  written against the previous release — which signed the bare body and sent no
  timestamp — MUST be updated, and should start rejecting requests whose
  timestamp is more than five minutes off its own clock;
- **`X-Webhook-Delivery` now carries the `event_id`**, not the delivery row's
  id, so it repeats across retries of one event and is the value to deduplicate
  on, exactly as the target says;
- **The delivery body is now the documented envelope**
  `{id, event, created_at, data}` rather than the raw internal event. One
  caveat: `data` carries the domain event's own fields, which are close to but
  not identical to the resource this API returns — a transaction arrives with
  `transaction_id`, `amount` and `currency_code` rather than `id` and a `money`
  object. Treat `data` as the event, not as a resource you can hand to code
  written against `GET /transactions/{id}`;
- **Rotating a secret keeps the previous one valid for 24 hours.** New
  deliveries are signed with the new secret; a delivery already queued when you
  rotated is still signed with the secret it was queued under until that window
  closes. Hold both secrets during the changeover and accept a match against
  either. Rotating a second time inside the window invalidates the older secret
  immediately — only two are ever live.
