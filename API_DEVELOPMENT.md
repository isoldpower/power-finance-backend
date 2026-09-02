# Planned API work
Everything deliberately left out of [API_TARGET.md](./API_TARGET.md). That document describes the
API as it should be NOW; this one is the queue behind it.

Nothing here is a contract. Shapes are sketches, not specifications — they exist to record intent
and to make the eventual design decision cheaper, not to be implemented as written.

## Transactions

### Adjustment transactions
A transaction whose purpose is to correct another transaction's value, rather than to record a new
money flow. Referenced in the Transactions intro of the target doc as explicitly out of scope.

Open questions:
- Does an adjustment reference the transaction it corrects, or the wallet, or both?
- Is the original left intact with the adjustment layered on top (audit-friendly), or is the
  original superseded? The former keeps history honest and is probably right for a ledger;
- Does an adjustment participate in the AI posting generation the same way, or does it inherit the
  original's account mapping?
- Should `type` gain an `adjustment` member, or is this a separate `origin`?

### Sorting beyond `created_at`
Both `/search` endpoints currently take a single `order` param (ASC/DESC on `created_at`). The
browsers in the UI want to sort by amount and by name.

Sketch: a `sort_by` query param naming a whitelisted field, validated the same way filter fields
are, reusing the per-resource field policy. Per-leaf sorting inside `filter_body` is a separate and
much larger idea — not this.

### Deleted-resource access
Soft deletes are invisible today: closed wallets, closed goals and cancelled transactions leave every
list and search, and nothing brings them back.

Two pieces:
- An `include_deleted` boolean query param on list and `/search` endpoints, defaulting to `false`;
- A restore endpoint per soft-deletable resource, clearing `deleted_at`. `POST /wallets/{id}/restore`
  is the obvious shape. Needs a rule for restoring into a state that has since become invalid — a
  wallet whose currency was retired, a goal whose `finish_at` has passed;

### Stored categories
`category` on transactions accepts any string today, and the target doc says so. It becomes a
reference to a stored category later.

Needs:
- A category resource with its own CRUD, and a listing endpoint the forms can populate from;
- A migration path for the free-form strings already recorded — match by name, or park unmatched
  ones in an "uncategorised" bucket rather than dropping them;
- A decision on whether categories are type-specific (different sets for `income` and `expense`) or
  one flat set. Type-specific is what the original notes assumed;
- The point at which free-form values stop being accepted is a BREAKING change under the versioning
  rules — tightening validation on an existing field. It cannot ship inside `v1`;

Wallet `category` is the same story on a different resource: any string today, a predefined set plus
user-created labels later.

## Actions
Specified in the target doc. What was left out:

- **Nothing raises a time-triggered action yet.** The producer plumbing is built and running — the
  `group_key` collapse, the expiry sweep, and `RaiseActionCommand` as the seam a scheduled job would
  call. What is missing is a CONDITION to check. The target's own example is "a subscription
  charging tomorrow against a wallet that cannot cover it", and this system models neither
  subscriptions nor recurring charges, so there is nothing to schedule a check against. Modelling
  recurring charges is the prerequisite and is a slice of its own, not a piece of Actions;
- **Bulk resolve.** Answering the whole queue in one request. Straightforward, but wants a decision
  about partial failure — all-or-nothing, or per-item results in the response;
- **Undo.** Resolving with `applies: true` moves real data and there is no way back except doing the
  inverse by hand. An `unresolve` would have to reverse the applied effect, not just flip `status`,
  so it is a bigger idea than it looks;
- **The Notifications boundary.** An action is something the user must DECIDE; a notification is
  something the user is TOLD. They are separate resources on purpose. Whether one action should also
  raise a notification — "your subscription failed and you never answered" — is unsettled;
- **Snooze.** `expires_at` exists but nothing lets a user push it. A `defer` resolution that
  reschedules rather than resolves is the obvious shape;

Explicitly REJECTED, so it is not proposed again: server-driven forms. Field descriptors or embedded
schemas inside a resolution, letting the backend define input UI. It turns the API into a form engine
with its own versioning problem. Actions that need input deep-link to the flow that already exists.

## Notifications
Specified in the target doc. What was left out:

- **Acknowledge all.** A bell menu wants one button that clears the badge. Trivial as
  `POST /notifications/ack`, but it needs a rule for what "all" means when the list is filtered —
  everything, or everything matching the current filter;
- **Deletion.** Notifications accumulate forever and nothing removes them. Either a retention policy
  the user never sees, or a `DELETE`, or both. Retention alone is probably right;
- **Per-severity or per-kind muting.** No way to say "stop telling me about this". Related to
  user preferences, which now live outside this API entirely — so muting rules would be the first
  preference that genuinely needs to be server-side and queryable;
- **Grouping.** Actions collapse recurrences through `group_key`. Notifications do not, so a noisy
  producer floods the feed. Worth revisiting once real producers exist rather than guessing at it;

## Automations
Specified in the target doc, and built. The run ledger that makes a run happen
once — `automation_runs` — grows a row per rule per subject and has **no
retention policy**; that is the one piece of this slice that will need attention
before it is long-lived, and it is the same table a run-history endpoint would
be served from. What was left out:

- **Dry run.** "How many transactions would this match?" before saving. The single most useful thing
  missing — a rule the user cannot test is a rule they are guessing at. Cheap to build, since the
  condition is already a `filter_body` and `POST /transactions/search` already answers exactly this
  question. Likely a `POST /automations/preview` taking an unsaved trigger and returning a count plus
  a sample;
- **Backfill.** Applying a new rule to existing data. Deliberately excluded — it is a bulk mutation
  driven by a rule the user has never seen run, and it needs an undo story before it needs an
  endpoint;
- **Run history.** `last_run_at` and `runs` are counters, and the ledger behind them records only
  THAT a rule ran on a subject, not what each effect did. A `GET /automations/{id}/runs` is most of
  the way there — it wants the per-effect outcome stored alongside the claim, and the retention
  policy that table needs anyway;
- **Explicit priority.** Evaluation order is `created_at ASC` and last-write-wins, which is
  predictable but not controllable. A `priority` field would let the user order rules directly;
- **Richer effects.** `set_category` is the only field-setting effect. Setting a wallet, adding a
  label, or splitting a transaction are all plausible and all additive;
- **More trigger events.** Only `transaction.created` and `transaction.updated` exist. Wallet balance
  crossing a threshold is currently expressible only as a scheduled rule with a filter, which checks
  periodically rather than at the moment it happens;

Explicitly REJECTED, so it is not proposed again: a free-text rule DSL. The UI mock typed conditions
as strings (`merchant ~ "coffee"`, `set category Dining`), which requires a parser, a grammar,
position-accurate error reporting and autocomplete before it is usable — and then that grammar is a
versioned public contract of its own. The structured `filter_body` tree does the same job with a
validator that already exists.

## Webhooks
Specified in the target doc, including the delivery contract. What was left out:

- **Test delivery.** `POST /webhooks/{id}/test` sending a synthetic event. The cheapest possible
  improvement to setup — right now the only way to know an endpoint works is to wait for real
  activity. Needs a decision on whether the test event appears in the delivery log;
- **Manual redelivery.** `POST /webhooks/{id}/deliveries/{delivery-id}/retry` for a delivery that
  exhausted its attempts while the receiver was down. Without it, a failed delivery is lost and the
  only recovery is a full resync the API cannot perform;
- **Auto-disable.** A permanently dead endpoint is retried 5 times per event forever. Standard
  behaviour is to disable it after N consecutive failed deliveries and raise a notification. Needs a
  threshold and a re-enable path;
- **Delivery log retention.** The table grows without bound and nothing prunes it, and the log
  deliberately outlives the endpoints it belongs to, so deleting webhooks does not bound it either;
- **Exponential backoff.** Retries back off LINEARLY — attempt *n* waits `n × 30s`, so five attempts
  span about 7.5 minutes rather than the flat 2 the target's Retries section describes. Still the
  wrong shape for a receiver that is down for an hour. Exponential with jitter, and more attempts
  over a longer window, is the usual fix;
- **Payload in the delivery log.** Stored but not exposed. Useful for debugging, at the cost of page
  size and of restating superseded money;

## Assistant
Specified in the target doc. What was left out:

- **Named conversations.** One rolling thread per user today. Multiple threads with their own titles
  and history is a product decision, not a technical one. The endpoints are shaped so it arrives as a
  conversation id in the path rather than a restructure;
- **Resumable generation.** A dropped connection loses the live view; the answer is recovered by
  refetching. True resume means a replayable per-message stream — `GET /assistant/messages/{id}/stream`
  with an offset — and it is only worth it if long answers turn out to be common;
- **Stop generation.** No way to cancel a reply in flight. Wants a `DELETE` on the in-flight message
  or an abort signal, plus a decision on whether the partial text is kept;
- **Inline reference anchors.** `refs` is a flat list, so a client cannot underline the phrase a
  citation belongs to. Doing better means the model emitting offsets or markup, which is a
  meaningfully harder generation problem than emitting a list of ids;
- **Feedback.** No thumbs up/down on a reply, so there is no signal for improving answers;
- **Attachments.** Sending a receipt image into the chat overlaps with the Media upload and Receipt
  scan slices, and should be designed with them rather than before them;
- **Quota visibility.** Requests are rate limited but a client cannot see how much budget is left,
  so it cannot warn before the user is cut off;

### What-if simulation
The planning-side sandbox — branch the finances, change incomes or goals, watch runway and goal ETAs
move without touching real data. Currently a "coming soon" card in the UI with no endpoint behind it.

It belongs to the assistant surface but is a genuinely separate problem: a simulation is a stateful
scenario the user edits over time, not a question with an answer. It needs its own resource, and
whether scenarios are persisted or evaluated per-request is the first decision.

## Accounts

### Manual entry adjustment
Accounts and their entries are dispatched by AI at the backend and are entirely read-only in the
target doc. The user needs a way to correct a misfiled entry.

Open questions:
- Is the correction an edit of the dispatched entry, or an overriding user-authored entry that
  shadows it? The second keeps the AI output auditable and makes "what did the model do" answerable;
- Does correcting one entry retrain or re-dispatch anything else, or is it purely local?
- Does the chart of accounts itself become user-editable, or only the dispatch of entries into it?

## Pagination

### Addressable pages (snapshot + page)
The target doc paginates by keyset, which deliberately gives up random access: "page 7" is reached
by walking pages 1 through 7. That is the accepted behaviour for now. This entry records the design
to reach for IF a screen turns out to need real numbered page buttons — so the decision is not
re-derived from scratch under deadline.

**Do not build this speculatively.** It is a second way to address the same ordering and a second
code path through every paginated query. Next/previous plus a `meta.total` readout ("25 of 187")
covers most tables. Confirm a screen genuinely needs numbered buttons first.

#### Why not plain offset
Because it reintroduces exactly the drift keyset removed — page 4 holds different rows before and
after an insert, so paging repeats and skips rows. That is a property of counting positions in a
live collection, not of any particular syntax, so it cannot be fixed by naming the param something
else.

#### The mechanism
Freeze the collection, then count inside the frozen window.

The first request captures a boundary — the newest `(sort_key, id)` at that instant — and returns it
as an opaque `snapshot` token. Later requests send the token plus a page number, and the server
offsets INSIDE that window:

```
WHERE (created_at, id) <= :snapshot
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET (:page - 1) * :limit
```

Rows created after the snapshot are excluded from the whole paging session, so page 4 holds the same
rows on the way back as it did on the way there, and `total` does not move under the pager.

Sketch:

| param    | type   | note                                                        |
|----------|--------|--------------------------------------------------------------|
| `page`   | Number | 1-based. Requires `snapshot`                                |
| `snapshot` | String | opaque boundary token, minted on a request that omits it  |

`meta` in this mode gains `page`, `pages`, and `stale_count`, and reports both cursors as `null`.
`stale_count` is how many rows now exist newer than the snapshot — one counted comparison against
the boundary. It is what lets the UI render a "3 new transactions" pill instead of hiding the
staleness.

New error code: `pagination_mode_conflict` (422), when `page` and `cursor` arrive together.

#### The staleness, stated honestly
The snapshot freezes only which rows are IN this list for this paging session. Edits to rows already
inside the window read live, deletions apply normally, and no other endpoint or aggregate is
affected. But new rows genuinely do not appear until the token is dropped.

Two client obligations make that safe, and both are mandatory rather than advisory:

- **Drop the snapshot when the user returns to page 1.** Requesting page 1 without a token mints a
  fresh one. This is what keeps the common case live;
- **Drop the snapshot after any mutation the client performs.** Otherwise the user creates a
  transaction and does not see it in the list — which in a finance app reads as money vanishing, and
  is far worse than the duplicated row keyset was introduced to prevent. Note the Read-At-Least
  mechanism does NOT cover this: it guarantees the read side caught up to the write, but cannot
  place a row inside a window that explicitly excludes it;

#### Likely scope
Only endpoints whose UI has a numbered pager — probably `POST /transactions/search`,
`POST /wallets/search`, and `GET /goals`. Both modes run over the same ordering, so the sort contract
in the target doc does not change; only the way a position in it is addressed.

Deep offsets stay slow (`OFFSET 10000` scans and discards 10000 rows), which is irrelevant at this
project's scale and would not be at another's.

## Platform

### Realtime beyond notifications
GET /notifications/stream is specified in the target doc and is the only stream that exists. The
remaining candidates, roughly in order of value:

- **Balance and metrics invalidation** after a write lands in the read model — the UI has no way to
  know its projection moved. Note this one CANNOT copy the notifications pattern: those events must
  be THIN (an id or a bare "refetch" signal), never a payload carrying a figure. A fat event carrying
  a balance races the read model and shows a number the next read contradicts, which is the exact
  problem `Read-At-Least` exists to solve;
- **Actions** appearing in the queue — same shape as notifications, and fat events are safe there for
  the same reason;
- **AI assistant chat** token streaming, which is a different kind of stream: one response
  progressively delivered rather than discrete events, and it likely wants its own endpoint shape;

The open question across all of them is whether they stay per-slice or merge into a single
app-wide `GET /events` with a typed envelope. Per-slice is where this starts. Merging matters once
three or more streams are open per tab, since that is connection pressure for no benefit; it is a
client-side change and breaks no contract.

### Server-side preference reads
RESOLVED for the client, still open for the backend. Preferences (`currency`, `timezone`,
`language`) live in Clerk `unsafeMetadata` and are specified in the target doc under Conventions →
User Preferences. There is no user resource and no auth endpoint to build: Clerk issues, refreshes
and revokes tokens, and the target doc already specifies the API's whole side of that.

What remains is how the BACKEND reads those values, which differs by caller and does not affect the
contract:
- **Async work** — notifications, AI generation, outbound webhooks, automations. No request exists
  to carry the value, so these read the Clerk Backend API directly. Latency is irrelevant there;
- **Request path** — currency conversion in Metrics, the `last_month` boundary. These must NOT call
  Clerk per request; that is a third-party hop plus their rate limits on every dashboard load.
  Either forward the values as gateway-set headers off the JWT claims, or accept the values from the
  client, which already holds them;

If the claim route is taken: the `clerk-jwt` plugin already parses the full payload into
`kong.ctx.shared.clerk_claims` and forwards only `sub`. Any added header must be set or cleared
UNCONDITIONALLY. A `if claim then set_header end` leaves a client-supplied header intact when the
preference is unset, letting a caller choose its own reporting currency.

Preferences move out of `unsafeMetadata` and into a real resource if they ever grow past a few
scalars — dashboard layout, notification settings, default wallet — or if a bad value starts
breaking async jobs rather than one screen. Neither is true today.

## Slices not yet specified
Known future surface, listed so it is not mistaken for an oversight. None of it is in the target
doc:

| slice                | note                                                        |
|----------------------|-------------------------------------------------------------|
| Categories           | replaces the `category: null` placeholder throughout        |
| Wallet kinds         | the wallet type vocabulary                                  |
| Receipt scan         | upload → extracted fields                                   |
| Media upload         | the missing producer of `evidence.url`                      |
| What-if simulation   | planning-side projection                                    |

## Smaller open items
- **Per-wallet balance history.** Wallet detail exposes a `last_month` inflow/outflow aggregate but
  no series, so a per-wallet chart has nothing to draw;
- **Budget vs actual.** No budget concept exists anywhere in the API yet;
- **Batch reads / field selection.** A dashboard load fans out into many small requests. A batch
  endpoint or a `fields=` selector would cut it down, at the cost of a much fussier contract. Worth
  measuring before building;
- **`origin` vocabulary.** The target doc only ever shows `manual`. If imported and recurring
  transactions are real, they need the endpoints that produce them;
