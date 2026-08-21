# This document describes the desired API structure
It includes the description for each slice, the general structure and specifics.

The surface described here is REST, with TWO exceptions, each documented in its own section alongside
the conventions it does not follow: GET /notifications/stream and POST /assistant/messages both
respond with Server-Sent Events. Every other realtime transport — a WebSocket, a stream for any other
slice — is out of scope for this revision and tracked in
[API_DEVELOPMENT.md](./API_DEVELOPMENT.md) along with everything else planned but not yet specified.

## Conventions
Rules in this section apply to every endpoint in this document. Slice sections below only describe
what is specific to them; they never redefine the envelope, the error shape, or the idempotency contract.

### Versioning
Every endpoint lives under a single versioned base path:

```
/api/v1
```

Endpoint headings throughout this document are written relative to that prefix. `GET /transactions`
means `GET /api/v1/transactions`. There are no unversioned endpoints — if a liveness or readiness
probe is added later it sits outside `/api` entirely and is not part of this contract.

Rules:
- The version is a path segment, not a header and not a query param. It stays visible in access
  logs, is trivially curl-able, and lets a cache or a proxy route two versions apart without
  inspecting anything but the URL;
- Only the MAJOR version appears. There is no `/api/v1.2`. Minor evolution is additive and does not
  move the URL;
- `v1` is the whole surface described here. A client pinned to `/api/v1` may rely on every field,
  `error.code`, status code, and default documented in this file remaining as written;

#### Additive Changes
These ship inside `v1` without notice. Clients must tolerate them:

- A new endpoint;
- A new OPTIONAL query param, or a new optional field in a request body;
- A new field in a response object;
- A new member in an enum-like field;
- A new `error.code` or `error.details[].code`;

#### Breaking Changes
These require `/api/v2`. They are never made in place:

- Removing or renaming a field, or moving it between `data` and `meta`;
- Changing a field's type or nullability — including the number/string distinction that
  `amount` depends on;
- Changing what an existing `error.code` means, or the HTTP status it is returned with;
- Tightening validation on an existing field, or making an optional field required;
- Changing a documented default, such as the `limit` of 25 or the `category` of `all`;
- Removing an enum member;
- Any change to the response envelope itself;

#### Client Obligations
The additive/breaking split only holds if clients hold up their end. A `v1` client MUST:

- Ignore response fields it does not recognise rather than failing to parse;
- Treat an unrecognised enum value as an unknown-but-valid case, not an error. A client that
  switches exhaustively over `type` or `origin` turns every future category into an outage;
- Never depend on JSON key order, or on the absence of a key it does not use;

Without these, every additive change becomes breaking in practice and the version loses its meaning.

#### Deprecation
When `v2` arrives, `v1` keeps serving for a documented overlap window — both prefixes live side by
side, and `v1` is not switched off at the moment `v2` ships. During the window `v1` responses carry
the `Deprecation` and `Sunset` HTTP headers so a client can detect its own staleness without anyone
reading a changelog.

### Authentication
Every endpoint requires a bearer token. There are no anonymous routes.

```
Authorization: Bearer <token>
```

Rules:
- The token is validated at the gateway before the request reaches any service. A missing,
  malformed, or expired token fails with 401 `unauthorized` and never touches a handler;
- The gateway resolves the token into an internal identity and forwards it downstream. Services
  never parse the token themselves, and the client never sends a user id — an `X-User-Id` supplied
  by a client is ignored, not trusted;
- Every resource in this document is scoped to the authenticated user. There is no cross-user
  access, no sharing, and no admin view;
- A resource belonging to ANOTHER user returns 404 `not_found`, not 403 `forbidden`. 403 would
  confirm the id exists, turning every UUID path in the API into an existence oracle. 403 is
  reserved for a resource the caller owns but may not act on in that way;

### User Preferences
Three user-level settings change what several endpoints in this document return. NONE of them are
part of this API. There is no `/me`, no user resource, and no endpoint that reads or writes a
preference.

They live on the user record at the identity provider (Clerk), in `unsafeMetadata`:

| field      | format             | consumed by                                          |
|------------|--------------------|------------------------------------------------------|
| `currency` | ISO-4217 code      | every figure in Metrics; any server-side conversion   |
| `timezone` | IANA name          | server-computed relative windows — today only `last_month` on wallet detail |
| `language` | BCP-47 tag         | backend-generated prose. Nothing in this document yet |

The point of storing them there is that BOTH sides already read that record — the client through the
Clerk SDK, the backend through Clerk — so there is one source of truth and no synchronisation to
build. Preferences never travel this API in either direction, and no projection, replication or
cache invalidation exists for them.

Rules:
- The client writes preferences through the Clerk SDK, not through this API. A preference change is
  NOT a write in the sense of the Consistency section: it emits no `X-Write-Version`, and
  `Read-At-Least` has nothing to say about it;
- `unsafeMetadata` is client-writable by design, which means these values are UNTRUSTED INPUT
  wherever the backend reads them. A `currency` not present in `GET /currencies`, a `timezone` that
  is not a real IANA name, or any absent field falls back to the documented default below. It is
  never an error and never propagates as one — a bad preference degrades presentation, it does not
  fail a request;
- Defaults, applied per-field whenever the stored value is missing or unrecognised:
  `currency` = `USD`, `timezone` = `UTC`, `language` = `en`;
- Because a preference is not an API write, a client that changes one is responsible for refetching
  whatever depended on it. Nothing invalidates on the server, and a cached response (`meta.cached`)
  may still carry the previous currency;
- Preferences are per-user and never appear in a response body. A currency code inside a money
  object states what that amount IS, not what the user prefers;

NOTES:
- Money SCALE is not a preference. The digit count comes from the currency itself — see Money Shape
  — so a user preference can select which currency is reported, never how it is formatted;
- Number, date and text FORMATTING are entirely client-side. This API emits unformatted decimal
  strings and offset-bearing ISO-8601 timestamps precisely so that no formatting decision has to
  cross it;
- `language` is listed for completeness and currently selects nothing: no endpoint in this document
  returns backend-generated prose. It becomes load-bearing with the Assistant and Notifications
  slices, which are not specified here. Error `message` strings are NOT translated — the `code` is
  the contract and the client renders from that;

### Consistency
Reads and writes are served by different services and the read side is eventually consistent. A
client that writes and immediately reads back would otherwise see stale data. The API exposes an
opt-in read-your-writes mechanism instead of pretending the lag does not exist.

| header            | direction | purpose                                                         |
|-------------------|-----------|------------------------------------------------------------------|
| `X-Write-Version` | response  | version stamp assigned to a successful write                     |
| `Read-At-Least`   | request   | minimum version the read must have caught up to before answering |

Flow:
- Every successful mutation returns `X-Write-Version`. It is an opaque, signed string — clients
  store and echo it, they never parse, compare, or construct it;
- A subsequent read that must observe that write sends the value back as `Read-At-Least`. The read
  side answers only once its projection has caught up;
- A client that does not track versions still gets read-your-writes: when `Read-At-Least` is absent
  the gateway injects the caller's last known write version automatically. Sending the header is an
  optimisation for clients that want to be explicit, not a requirement;
- A forged or tampered `Read-At-Least` is rejected at the gateway. The signature is what makes the
  header safe to accept from a client at all;
- When the read side has not caught up, the gateway transparently reroutes the request to the
  write side rather than failing. The staleness is resolved before the client sees it, so no error
  code in this document covers it;

NOTES:
- This is the API's answer to lost updates as well. Two clients editing the same wallet each read at
  their own write version, so neither silently reads a projection older than its own last write;
- The `/search` endpoints are READS despite being POST. They honour `Read-At-Least` like any other
  read and do NOT emit `X-Write-Version`. The method is dictated by the filter tree in the body, not
  by any state change;

### Rate Limits
Limits are enforced in two tiers: an IP floor that applies to every request, and a stricter per-user
ceiling that applies once the caller is authenticated. For normal traffic the per-user tier is the
one that bites.

| route class            | per-user / minute | per-user / hour | IP / minute | IP / hour |
|------------------------|-------------------|-----------------|-------------|-----------|
| reads (GET, `/search`) | 600               | 20000           | 1200        | 30000     |
| writes (POST/PATCH/DELETE) | 60            | 1000            | 200         | 5000      |

Rules:
- Read limits are deliberately wide. The UI is pagination-heavy and a single page view can fan out
  into a dozen reads;
- Remaining budget is reported on every response through `X-RateLimit-Limit-Minute`,
  `X-RateLimit-Remaining-Minute`, `X-RateLimit-Limit-Hour`, and `X-RateLimit-Remaining-Hour`. Only
  the per-user tier publishes headers, so clients see one consistent set of numbers regardless of
  which tier is closer to firing;
- Exceeding either tier fails with 429 `rate_limited` and a `Retry-After` header;
- The IP floor is checked BEFORE the token is verified, so spraying invalid tokens is capped by IP
  rather than burning verification work;

### Response Envelope
Every REST response — success or failure — is a JSON object with exactly two top-level keys.
On success it is `data` + `meta`. On failure it is `error` + `meta`. `data` and `error` are
mutually exclusive and never both present.

```json
{
	"data": {},
	"meta": {}
}
```

Rules:
- `data` is never omitted on success and is never `null`. Single-resource endpoints put an object
  there, collection endpoints put an array;
- `meta` is never omitted and is never `null`. When an endpoint has nothing to report it is `{}`;
- Mutations (POST/PATCH/PUT/DELETE) return the affected resource in `data`, in the PREVIEW shape;

#### Preview and Detail
Each resource has exactly two shapes, and every endpoint returns one of them:

| shape   | returned by                                    | contents                                    |
|---------|------------------------------------------------|---------------------------------------------|
| preview | list endpoints, `/search`, and ALL mutations    | the resource's own fields                   |
| detail  | single-resource GET (`/{id}`) only              | preview + embedded collections and analysis |

- A mutation returns exactly what a list item of the same resource carries — no more. `POST /wallets`
  returns the same object shape as one element of `GET /wallets` data, and `PATCH /transactions/{id}`
  the same shape as one element of `GET /transactions`. Nothing embedded, nothing paginated;
- This keeps a mutation's cost bounded and predictable. Detail shapes embed paginated collections
  (`postings`, `history`, `recent`), and building those on the way out of a write is work the caller
  did not ask for and usually discards;
- It also means a mutation response can be written straight into a list cache without reshaping,
  which is what clients actually do with it;
- When a client needs the detail shape after a write, it re-reads `GET /{resource}/{id}`. That read
  is the one place embedded collections are built;
- Because mutations return no embedded collection, their `meta` is `{}` apart from
  `idempotent_replay` where idempotency applies. Mutations never carry a pagination block;

### Meta Shape
`meta` carries transport concerns only — pagination, echoed request params, replay markers. It never
carries domain data. Domain data belongs in `data`.

When `data` is an array, `meta` MUST contain the pagination block:

| key           | type          | purpose                                                        |
|---------------|---------------|-----------------------------------------------------------------|
| limit         | Number / null | page size actually applied. `null` on non-paginated endpoints   |
| total         | Number        | total number of items matching the request, ignoring pagination |
| next_cursor   | String / null | token fetching the page after this one. `null` when exhausted   |
| prev_cursor   | String / null | token fetching the page before this one. `null` on the first page |

When `data` is an object that embeds a paginated collection (`history`, `postings`, `recent`, …),
the same block is namespaced under `meta` by the field name it paginates:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"history": []
	},
	"meta": {
		"history": {
			"limit": 10,
			"total": 42,
			"next_cursor": "Y3Vyc29yOnYxOjE3NjcyMjU4NjA6MTY2NWI2MGU",
			"prev_cursor": null
		}
	}
}
```

Every GET response additionally carries a cache marker:

| key    | type | purpose                                                       |
|--------|------|----------------------------------------------------------------|
| cached | Bool | `true` when the payload was served from cache rather than rebuilt |

It exists so a stale-looking screen can be diagnosed without reproducing it — the answer to "is this
the cache or the projection" is in the payload the user already has. Clients do not branch on it;
it is diagnostic, not control flow. Mutations do not carry it.

The `/search` endpoints carry it too. They use POST only because a filter tree does not fit a query
string — they create nothing, mutate nothing, and are reads in every respect that matters here. See
Consistency for the other half of that rule.

Endpoints may add their own keys to `meta` alongside the reserved ones (echoed filters, `since`,
`points`, and so on). Those extra keys are documented per endpoint.

NOTES:
- `count` is deliberately NOT part of `meta`. It is always `data.length` (or the length of the
  namespaced collection) and duplicating it only creates a way for the two to disagree;
- `has_more` is not part of `meta` either, for the same reason. It is exactly
  `next_cursor !== null`;
- Pagination is keyset-based across the whole API. There is no `offset`;
- Response examples in this document abridge the `data` array for readability, and omit
  `meta.cached` since it is present on every GET. `meta` otherwise describes a real request, so
  `data.length` in an example may be smaller than `meta.limit`;
- Cursor values in the examples are illustrative. They are opaque and their internal structure is
  not part of the contract;

### Pagination
Pagination is KEYSET-based. A page is identified by where the previous page ended, never by how many
rows to skip. Every paginated endpoint takes the same two query params with the same defaults. Slice
sections below repeat them for convenience but never change their meaning.

| param  | values | default | bounds  |
|--------|--------|---------|---------|
| limit  | Number | 25      | 1..100  |
| cursor | String | absent  | opaque  |

#### Why Not Offset
`offset` counts POSITIONS, and positions move. Every collection in this API is ordered newest-first
and grows at the head, which is the worst case for it.

Read 25 transactions at `offset=0`. Before the client asks for the next page, one transaction is
created. It becomes row 1 and shifts everything down. The client asks for `offset=25`, expecting
rows 26–50, and gets what were rows 25–49 — the last row of page one arrives a second time. Deletion
does the mirror: a row shifts up out of the requested window and is never seen at all.

Keyset asks "give me what comes after THIS row" instead of "skip 25 rows". Inserts and deletions
elsewhere in the collection cannot move the anchor, so pages neither repeat nor skip.

#### Cursors
- A cursor is an OPAQUE string. Clients store it and send it back verbatim. They never parse it,
  construct it, compare two of them, or persist one across sessions;
- Requesting a collection WITHOUT `cursor` returns the first page. Requesting it with the
  `next_cursor` from the previous response returns the page after it, and with `prev_cursor` the
  page before it. Direction is encoded in the cursor itself — there is no separate direction param;
- `next_cursor` is `null` on the last page. `prev_cursor` is `null` on the first. A collection that
  fits in one page has both `null`;
- A cursor is bound to the query that produced it — the sort order, and for `/search` the entire
  filter tree. Sending it back with a different `order` or a different `filter_body` fails with 422
  `cursor_mismatch` rather than silently paging through a different result set;
- A malformed, truncated, or unreadable cursor fails with 422 `cursor_invalid`;
- Cursors do not expire on a timer. A cursor whose anchor row has since been deleted still resolves
  — it describes a position in the ordering, not a row that must exist;

#### Ordering
Keyset requires a TOTAL order. Every paginated collection in this API — top-level and embedded
alike — is REVERSE-CHRONOLOGICAL, newest first:

```
created_at DESC, id DESC
```

`id` is the final tiebreaker on every collection without exception. Two rows sharing a timestamp can
never swap between requests, which is what makes an anchor stable. Where an endpoint documents an
`order` param, it flips every key together.

Two collections insert a key into that order. Both are documented on their endpoint as well:

| collection    | ordering                                              |
|---------------|--------------------------------------------------------|
| wallets       | `favorite DESC, created_at DESC, id DESC`             |
| transactions  | `created_at DESC, chain_id ASC NULLS LAST, id DESC`   |
| actions       | `severity DESC, created_at DESC, id DESC`             |

**Wallets** put favorites first. A leading key is applied AFTER filtering, never before — favorites
do not bypass a filter. A `/search` that excludes a favorite wallet excludes it, and the favorites
that do match simply lead the results.

**Actions** put the most urgent first — `critical`, then `warning`, then `info`. A `critical` action
from Tuesday outranks an `info` raised this morning, because the queue exists to be worked through in
priority order rather than read as a feed. `severity DESC` is ordered by the rank of the enum member,
not alphabetically.

**Transactions** group chain members together. Every transaction created by
POST /transactions/chains shares the chain's commit timestamp, so `chain_id` sorting below
`created_at` makes the legs of a transfer contiguous rather than interleaved with unrelated
transactions committed in the same instant. Standalone transactions carry `chain_id: null` and sort
last within their timestamp, so a `null` group never splits a chain.

NOTES:
- Contiguous is not the same as same-page. A chain can still straddle a page boundary — the last leg
  of a chain may be the first row of the next page. Ordering guarantees nothing is interleaved
  between the legs, not that they arrive in one response;
- `chain_id` is a tiebreaker, never a leading key. Leading with it would order the feed by UUID and
  destroy the reverse-chronological guarantee;
- Changing a key that a collection sorts on — toggling `favorite` — moves that row across page
  boundaries mid-session, exactly as editing a timestamp would. This is inherent to sorting on
  mutable data and is not a pagination defect;

#### Limit
- `limit` defaults to 25 when absent and is hard-capped at 100. There is no way to request an
  unbounded response — an unpaginated list is a page that silently breaks once the user's data grows;
- Out-of-range values are CLAMPED, not rejected: `limit=0` and `limit=-5` become 1, `limit=5000`
  becomes 100. Only a non-integer value fails, with 422 `validation_failed`;
- Because of clamping, `meta.limit` reports the EFFECTIVE page size, which may differ from what the
  request asked for;
- `limit` may change between pages. The cursor carries the anchor, not the page size;

#### What Keyset Costs
Page N is not directly addressable. "Page 7" is reached by WALKING — requesting pages 1 through 7 in
sequence, following each `next_cursor`. There is no jump.

This is accepted rather than worked around. A numbered pager is a positional question, and answering
it means counting rows in a collection that is still moving, which is the drift this design exists to
remove. Next/previous navigation and infinite scroll — the two access patterns the UI actually needs
— cost one request per page either way.

Consequences to design UIs around:
- A client MAY walk to reach a distant page, at one request per page. It is the client's decision,
  and it is a reasonable one for "page 3" and a bad one for "page 40";
- A UI cannot render numbered page buttons from this API. Next/previous with a position readout
  ("25 of 187") is the supported shape;
- Deep navigation should be replaced by narrowing, not by walking. `POST /search` with a date range
  reaches old rows in one request, which is both faster and closer to what the user meant;

An addressable-page mode is sketched in [API_DEVELOPMENT.md](./API_DEVELOPMENT.md). It is out of
scope here on purpose: it is a second way to address the same ordering, and a second code path
through every paginated query, which is not worth carrying until a screen genuinely needs it.

`meta.total` is still reported, so a UI can show "18 transactions", size a scrollbar, and render a
position readout without walking anything. It is a count of matching rows, unrelated to the current
page, and it may drift between pages exactly because the collection is live.

#### Non-Paginated Endpoints
A handful of endpoints return a fixed, small, complete set and are not paginated at all. They report
`"limit": null` with both cursors `null`, and always return everything. This is documented per
endpoint and is never the default.

#### Embedded Collections
`history`, `postings`, and `recent` paginate through their endpoint's `limit` / `cursor` params and
report their own block under `meta`, namespaced by field name. An endpoint embeds at most one
paginated collection, so there is never an ambiguity about which one `cursor` addresses.

They follow the same `created_at DESC, id DESC` ordering as everything else. For `postings` that
means the legs of one transaction share a timestamp and are separated only by `id`, so their order
is stable but carries no meaning — clients that want to show debits before credits sort on `debit`
themselves rather than relying on the order they arrive in.

### Money Shape
Monetary values are always an object carrying a decimal STRING and a currency code. The field is
named `amount` everywhere.

```json
{
	"amount": "10000.00",
	"currency": "USD"
}
```

`amount` is a string, not a JSON number. IEEE-754 doubles cannot represent most decimal fractions
exactly, and every JSON parser in the stack silently turns a number into one. `0.1 + 0.2` is the
canonical demonstration; in a ledger the same rounding shows up as balances that drift by a cent and
postings that refuse to sum to zero. Strings move the decision about arithmetic to the boundary
where it belongs — the client parses into its own decimal type and the server into `Decimal`.

#### Canonical Form
Every `amount` the server emits matches `^-?(0|[1-9][0-9]*)(\.[0-9]+)?$`. Specifically:

- No thousands separators, no currency symbol, no whitespace, no leading `+`;
- No exponent notation. `1e3` is invalid;
- No leading zeros on the integer part. `"007.00"` is invalid, `"0.07"` is not;
- The minus sign is the only sign, and it precedes the digits. Negative amounts are legal — a
  liability, a negative equity line, an overdrawn wallet;
- Negative zero is never emitted. Zero is `"0.00"` at scale 2, `"0"` at scale 0;
- `null` is never a valid amount. An unknown or inapplicable value omits the whole money object;

#### Scale
Responses are always emitted at the currency's own scale — the `decimals` value from
`GET /currencies`. A USD amount always carries exactly two fraction digits, a JPY amount exactly
zero. `"50"` is not a valid USD amount and `"50.00"` is not a valid JPY amount.

This makes responses stable: two amounts in the same currency are directly comparable as strings for
equality, and the client never has to guess how many digits to render.

Requests are laxer, because the client sends what the user typed:

- Fewer fraction digits than the scale are accepted and zero-padded. `"50"` in USD is read as
  `"50.00"`;
- No fraction digits and no decimal point are accepted. `"50"` is a valid USD request amount;
- MORE fraction digits than the currency allows are REJECTED with 422, detail code
  `amount_precision`. The server does not silently round money. `"50.005"` in USD fails rather than
  becoming `"50.00"` or `"50.01"` — which of those is right is the user's decision, not the API's;
- The integer part is limited to 18 digits. Beyond that the request fails with 422, detail code
  `amount_out_of_range`;
- A string that does not match the canonical grammar fails with 422, detail code `amount_malformed`.
  A JSON number where an amount is expected also fails with `amount_malformed`, so a client that
  regresses to numbers is caught immediately rather than losing precision quietly;

#### What Is NOT Money
These stay JSON numbers. They are counts, ratios, and factors, none of which participate in ledger
arithmetic:

| field                     | type   | why                                              |
|---------------------------|--------|--------------------------------------------------|
| `meta.limit` / `total`    | Number | item counts and page size                        |
| `decimals`                | Number | a digit count                                    |
| `net_diff.percentage`     | Number | a ratio, not an amount                           |
| `savings_rate`            | Number | a ratio, not an amount                           |
| `analysis.balanced`       | Bool   | —                                                |

Exchange rates are strings too, but they are NOT money and do NOT follow currency scale — a rate has
no currency of its own. Rates carry up to 12 fraction digits, trailing zeros are not padded, and
they are never rendered to the user without being multiplied out first.

NOTES:
- Do NOT use `value` as the money field name. `amount` is the single spelling;
- Request bodies that carry a single amount spell it flat, as `amount` + `currency` siblings, rather
  than nesting a money object. The string rules above apply identically to the flat form;
- Money is never compared, summed, or ordered as a string by the server beyond equality within one
  currency. Sorting and aggregation happen in `Decimal`;

### Timestamps
Every timestamp in this API is an ISO-8601 string with an explicit UTC offset, as in
`2026-08-12T11:51:00-05:00`. No bare dates, no epoch numbers, no offset-less strings.

Three timestamps are structural and appear on every resource that has them:

| field        | meaning                                        | when unset |
|--------------|------------------------------------------------|------------|
| `created_at` | when the resource was created                  | never unset |
| `updated_at` | when it was last modified                      | `null`     |
| `deleted_at` | when it was soft-deleted                       | `null`     |

`updated_at` and `deleted_at` are ALWAYS PRESENT. An unset one is `null`, never an omitted key. A
client can therefore read `resource.deleted_at` without guarding for the field's existence, and
`"deleted_at" in resource` is never a meaningful test.

Because every timestamp carries its own offset, a client-supplied instant is never ambiguous and
needs no timezone alongside it — `since` on the Metrics endpoints included. A timezone is required
only where the SERVER picks a boundary the client never stated, which in this document is
`last_month` on wallet detail. That boundary comes from the user's `timezone` preference; see
Conventions → User Preferences.

### Enumerations
Every closed vocabulary in this API, in one place. A field not listed here is free-form.

| field                | resource     | values                              |
|----------------------|--------------|-------------------------------------|
| `type`               | transaction  | `expense`, `income`                 |
| `origin`             | transaction  | `manual`, `scanned`                 |
| `group`              | account      | `assets`, `liabilities`, `equity`   |
| `net_diff.direction` | metrics      | `up`, `down`, `flat`                |
| `source`             | action       | `assistant`, `scheduler`            |
| `severity`           | action, notification | `info`, `warning`, `critical`  |
| `status`             | action       | `pending`, `resolved`, `dismissed`, `expired` |
| `resolutions[].intent` | action     | `primary`, `secondary`, `danger`    |
| `trigger.type`       | automation   | `event`, `schedule`                 |
| `trigger.event`      | automation   | `transaction.created`, `transaction.updated` |
| `trigger.schedule`   | automation   | `daily`, `weekly`, `monthly`        |
| `effects[].type`     | automation   | `set_category`, `notify`, `raise_action`, `transfer` |
| `status`             | delivery     | `pending`, `in_progress`, `retry_scheduled`, `success`, `failed` |
| `role`               | message      | `user`, `assistant`                 |
| `status`             | message      | `complete`, `streaming`, `failed`   |
| `signals[].tone`     | assistant    | `positive`, `negative`, `neutral`, `muted` |

Webhook `event` values are a closed vocabulary too, but they are served live by
GET /webhooks/event-types rather than listed here — the catalog grows independently of this document
and a copy in two places would drift.

NOTES:
- There is no `transfer` type. A transfer is a CHAIN of an `expense` and an `income` — see
  POST /transactions/chains — so the two legs are ordinary transactions and every balance
  calculation stays uniform;
- `flat` is a real `direction`, not a rounding artefact. Clients must render it rather than treating
  anything that is not `up` as `down`;
- Wallet `category` is deliberately NOT enumerated. It accepts any string today. A predefined set
  plus user-created labels is planned — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- Transaction `category` is likewise any string today, and becomes a reference to a stored category
  later. See the note on GET /transactions;
- Action `kind` is deliberately NOT enumerated and never will be. It is an open vocabulary that the
  assistant extends on its own, and the whole Actions design depends on clients not branching on it.
  `severity` is the closed field clients may branch on;
- Adding a member to any of these is an ADDITIVE change under the versioning rules, so clients must
  tolerate values they do not recognise;

### Filtering
Filtering is the job of the `/search` endpoints and only theirs. Plain `GET` collection endpoints
take pagination and their own documented params, never a filter — a filter tree does not survive a
query string legibly, and splitting the capability across both would leave two half-implementations.

`filter_body` is a tree of GROUP nodes and LEAF nodes. Groups combine, leaves compare.

```json
{
	"filter_body": {
		"and": [
			{
				"field_name": "currency",
				"operator": "eq",
				"value": "USD"
			},
			{
				"or": [
					{
						"field_name": "amount",
						"operator": "gte",
						"value": "100.00"
					},
					{
						"field_name": "wallet_id",
						"operator": "in",
						"value": [
							"1665b60e-bb7a-4360-8aa6-c1a578d81077"
						]
					}
				]
			}
		]
	}
}
```

#### Group Nodes
A group is an object with exactly ONE key, `and` or `or`, whose value is a non-empty array of child
nodes. Children may themselves be groups, so nesting is arbitrary.

- The keys are lowercase. `AND` is not accepted;
- An object carrying both `and` and `or`, or carrying a group key alongside anything else, is
  rejected — the grouping would otherwise be order-dependent;
- An empty array is rejected. "Match nothing" and "match everything" are both better expressed by
  not sending the group;

#### Leaf Nodes
A leaf is an object with exactly three keys: `field_name`, `operator`, `value`.

| operator    | meaning                        | value            |
|-------------|--------------------------------|------------------|
| `eq`        | equal                          | scalar           |
| `neq`       | not equal                      | scalar           |
| `gt`        | greater than                   | scalar           |
| `gte`       | greater than or equal          | scalar           |
| `lt`        | less than                      | scalar           |
| `lte`       | less than or equal             | scalar           |
| `in`        | member of                      | array of scalars |
| `contains`  | substring, case-sensitive      | scalar           |
| `icontains` | substring, case-insensitive    | scalar           |

#### Field Policies
Fields are whitelisted per resource. A field is filterable only if it appears below, and only with
the operators listed for it — the set follows from the field's type, so a datetime has no
`icontains` and a name has no `gte`. Anything outside the whitelist is rejected rather than ignored.

`GET /transactions` — filterable through `POST /transactions/search`:

| field         | type     | operators                        |
|---------------|----------|----------------------------------|
| `wallet_id`   | UUID     | eq, neq, in                      |
| `chain_id`    | UUID     | eq, neq, in                      |
| `amount`      | Decimal  | eq, gt, gte, lt, lte             |
| `currency`    | String   | eq, neq, in                      |
| `name`        | String   | eq, neq, in, contains, icontains |
| `category`    | String   | eq, neq, in, contains, icontains |
| `type`        | String   | eq, neq, in                      |
| `origin`      | String   | eq, neq, in                      |
| `created_at`  | Datetime | gt, gte, lt, lte                 |

`GET /wallets` — filterable through `POST /wallets/search`:

| field        | type     | operators                              |
|--------------|----------|----------------------------------------|
| `name`       | String   | eq, neq, in, contains, icontains       |
| `currency`   | String   | eq, neq, in                            |
| `balance`    | Decimal  | eq, gt, gte, lt, lte                   |
| `created_at` | Datetime | gt, gte, lt, lte                       |

NOTES:
- `value` is type-checked against the field. A datetime field takes an ISO-8601 string, a UUID field
  a UUID string, a decimal field a decimal string;
- Decimal fields follow the Money Shape grammar, so `amount` is compared as `"100.00"`, not `100`.
  The comparison is numeric, not lexical;
- For `in`, every element of the array is type-checked individually;
- Filtering is not sorting. Ordering is controlled by the `order` query param, documented per
  endpoint;
- These policies govern automation rule conditions too, not only `/search`. A rule's
  `trigger.filter_body` is validated against the policy of the trigger's subject resource, with the
  same operators and the same failure codes — see Automations;
- `name`, `category`, `type` and `origin` are filterable on transactions specifically so that a rule
  can express "a coffee purchase" without a separate condition language. They are useful on
  `POST /transactions/search` for the same reason;

#### Filter Failures
All filter problems are 422 `validation_failed`, distinguished by `error.details[].code`:

| detail code                   | cause                                                     |
|-------------------------------|-----------------------------------------------------------|
| `filter_unknown_field`        | `field_name` is not whitelisted for this resource         |
| `filter_operator_not_allowed` | operator is unknown, or not permitted on that field       |
| `filter_value_type`           | `value` does not match the field's type                   |
| `filter_malformed_group`      | group has zero or multiple keys, or a non-array / empty child list |
| `filter_malformed_node`       | node is neither a valid group nor a valid leaf            |

### Errors
Failures return the standard error envelope. HTTP status carries the class of failure, `error.code`
carries the machine-readable reason, `error.message` is human-readable and safe to log but NOT safe
to render verbatim to the user.

```json
{
	"error": {
		"code": "validation_failed",
		"message": "Request body failed validation",
		"details": [
			{
				"field": "amount",
				"code": "amount_precision",
				"message": "USD allows 2 fraction digits, got 3"
			}
		]
	},
	"meta": {
		"request_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"timestamp": "2026-08-12T11:51:00-05:00"
	}
}
```

Rules:
- `error.code` is a stable snake_case string. It is part of the API contract and may not change
  without a version bump. Clients branch on it, never on `error.message`;
- `error.details` is an array, present only for field-level failures (`validation_failed`). It is
  omitted otherwise, never `null`;
- `details[].field` is a JSON path into the REQUEST body, using bracket notation for array indices;
- `meta.request_id` is present on every error and is the value to quote in bug reports;

#### Status Codes

| status | when                                                                             |
|--------|----------------------------------------------------------------------------------|
| 200    | successful GET, PATCH, DELETE, and POST that does not create a resource (search) |
| 201    | successful POST that created a resource                                          |
| 400    | request is malformed — unparseable body, unknown query param, missing required header |
| 401    | no credentials, or credentials expired                                           |
| 403    | authenticated but the resource belongs to another user                           |
| 404    | resource does not exist, or is soft-deleted and the endpoint does not expose those |
| 409    | request conflicts with current server state — the state must change before a retry can succeed |
| 422    | request is well-formed but semantically invalid — the request itself must change |
| 429    | rate limited. `Retry-After` header is set                                        |
| 500    | unhandled server failure. `error.details` is always omitted                      |
| 503    | a dependency this endpoint needs is temporarily unreachable. Retrying is correct |

The 409/422 split matters: 409 means "retry later, after something else happens", 422 means
"this request will never succeed as written".

#### Error Codes

| code                        | status | raised by                                                        |
|-----------------------------|--------|------------------------------------------------------------------|
| `bad_request`               | 400    | any                                                              |
| `validation_failed`         | 422    | any endpoint with a request body                                 |
| `unauthorized`              | 401    | any                                                              |
| `forbidden`                 | 403    | any                                                              |
| `not_found`                 | 404    | any endpoint with a path parameter                               |
| `rate_limited`              | 429    | any                                                              |
| `internal_error`            | 500    | any                                                              |
| `idempotency_key_required`  | 400    | POST /transactions, POST /transactions/chains                    |
| `idempotency_key_reuse`     | 409    | any idempotent POST                                              |
| `idempotency_key_in_flight` | 409    | any idempotent POST                                              |
| `cursor_invalid`            | 422    | any paginated endpoint — cursor unreadable or malformed          |
| `cursor_mismatch`           | 422    | any paginated endpoint — cursor does not match the query it is sent with |
| `chain_cycle`               | 422    | POST /transactions/chains — `after` references form a cycle      |
| `chain_unknown_reference`   | 422    | POST /transactions/chains — `after` references an unknown `temporary_id` |
| `chain_too_long`            | 422    | POST /transactions/chains — more than 100 entries in one request  |
| `wallet_closed`             | 409    | POST /transactions — target wallet is soft-deleted               |
| `wallet_not_empty`          | 409    | DELETE /wallets/{wallet-id} — balance is non-zero                |
| `goal_not_empty`            | 409    | DELETE /goals/{goal-id} — progress is non-zero                   |
| `already_deleted`           | 404    | DELETE on an already soft-deleted resource, when not idempotent  |
| `assistant_unavailable`     | 503    | POST /assistant/messages — upstream model unreachable            |
| `subscription_exists`       | 409    | POST /webhooks/{webhook-id}/events — endpoint already subscribes to that event |
| `unknown_resolution`        | 422    | POST /actions/{action-id}/resolve — `resolution_id` is not offered on this action |
| `action_already_resolved`   | 409    | POST /actions/{action-id}/resolve — action is no longer `pending` |
| `unsupported_currency`      | 422    | any endpoint accepting a currency code                           |
| `rate_unavailable`          | 409    | GET /currencies/convert, GET /currencies/rates — no fresh rate   |

#### Detail Codes
`error.details[].code` is a separate, finer vocabulary describing what is wrong with ONE field. It
never appears at the top level, and the top-level codes above never appear inside `details`.

| code                   | meaning                                                              |
|------------------------|-----------------------------------------------------------------------|
| `required`             | field is absent and has no default                                   |
| `unknown_field`        | field is not part of the request schema                              |
| `amount_malformed`     | amount is not a canonical decimal string, or was sent as a JSON number |
| `amount_precision`     | amount carries more fraction digits than the currency allows          |
| `amount_out_of_range`  | integer part exceeds 18 digits                                        |
| `currency_mismatch`    | field's currency conflicts with another field's in the same request   |
| `not_a_reference`      | id-shaped field does not resolve to an existing resource              |
| `out_of_bounds`        | numeric field outside its documented range                            |
| `trigger_field_conflict` | `trigger` carries the field belonging to the other `type`           |
| `effect_unknown_type`  | `effects[].type` is not a documented effect                          |
| `effect_params_invalid`| effect `params` are missing, unknown, or wrongly typed for that type |
| `effect_subject_mismatch` | effect cannot apply to the trigger's subject resource             |
| `unknown_event_type`   | `event` is not present in GET /webhooks/event-types                  |
| `url_scheme`           | url is not absolute, or uses a scheme other than http / https        |

### Idempotency
Money-moving POST requests are idempotent through an `Idempotency-Key` request header. Without it a
dropped response or a double-tapped button creates duplicate transactions, which the API has no way
to detect after the fact.

```
Idempotency-Key: 1665b60e-bb7a-4360-8aa6-c1a578d81077
```

Rules:
- The header is REQUIRED on `POST /transactions` and `POST /transactions/chains`. Omitting it fails
  with 400 `idempotency_key_required`;
- The header is OPTIONAL on every other POST. When supplied it is honoured with the same semantics;
- The key is a client-generated UUID v4. It is scoped to the tuple (user, method, path, key) and is
  retained for 24 hours. After that window the key is forgotten and a replay creates a new resource;
- Replay with a body identical to the original returns the ORIGINAL response — same status code,
  same `data`, same resource id — with `meta.idempotent_replay` set to `true`. The server does not
  re-execute anything;
- Replay with a DIFFERENT body under the same key fails with 409 `idempotency_key_reuse`. The
  original resource is left untouched;
- Replay while the original request is still executing fails with 409 `idempotency_key_in_flight`.
  The client should retry the same key after a short backoff rather than generating a new one;
- Body comparison is done over a canonical hash of the request body. Header and query-param
  differences are ignored;

Every response to an idempotent-capable POST carries the marker, so clients can tell a fresh write
from a replay:

```json
{
	"data": {},
	"meta": {
		"idempotent_replay": false
	}
}
```

DELETE endpoints in this document are soft deletes and are naturally idempotent by resource id —
repeating them returns 200 with the same body rather than 404. They do not take an idempotency key.

## Accounts
Accounts are virtual ledger items that are used to manage and analyze money flow across the wallets,
calculate financial ratios and make advices based on the results.

Accounts are READ-ONLY in this revision. There is no create, update, or delete. The chart of
accounts and the entries dispatched into it are produced at the backend by AI from the user's
transactions — the same mechanism that generates transaction postings. Endpoints for manually
correcting a dispatched entry are planned; see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md).

### GET /accounts
REST request to access the categorized accounts list

#### Query Params
| param    | values                          | default | purpose                                                       |
|----------|---------------------------------|---------|----------------------------------------------------------------|
| group    | {assets/liabilities/equity/all} | all     | Specify the group of accounts to retrieve                      | 
| lowbar   | Decimal                         | 0       | Set the least value of the category to filter out small ones   |
| currency | CUR                             | USD     | Currency the `lowbar` threshold is expressed in                |
| cursor   | String                          | absent  | Opaque page token (see Conventions → Pagination)               |
| limit    | Number                          | 25      | Specify the amount of accounts to return (1..100, clamped)     |

#### Response Body

Example response body looks as follows:
```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"group": "assets",
			"name": "Emergency Fund",
			"money": {
				"amount": "10000.00",
				"currency": "USD"
			}
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"group": "assets",
			"name": "Inventory",
			"money": {
				"amount": "2000.00",
				"currency": "USD"
			}
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"group": "liabilities",
			"name": "Accounts Payable",
			"money": {
				"amount": "100.00",
				"currency": "USD"
			}
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"group": "equity",
			"name": "Retained Earnings",
			"money": {
				"amount": "11900.00",
				"currency": "USD"
			}
		}
	],
	"meta": {
		"limit": 25,
		"total": 4,
		"next_cursor": null,
		"prev_cursor": null,
		"lowbar": "50.00",
		"currency": "USD",
		"group": "all",
		"groups": {
			"assets": 2,
			"liabilities": 1,
			"equity": 1
		}
	}
}
```
NOTES:
- `meta.total` is the flat pagination total required by the envelope. The per-category breakdown
  lives in `meta.groups` and is NOT affected by the `group` filter — it always describes the
  full set so the UI can render group tabs with counts;
- The query param is `group`, matching the field on the resource. It was previously called
  `category`, which collided with the unrelated `category` on wallets and transactions;
- Ordered `created_at DESC, id DESC`, like every collection in this API. `group` filters, it does
  not order — assets do not lead liabilities;
- `lowbar` and `currency` are two separate params. They were previously one packed string
  (`0USD`), which every client and the server had to parse. `lowbar` follows the Money Shape
  grammar and is validated against `currency`'s scale;
- `meta` echoes both back, so a client can confirm what threshold was actually applied;

### GET /accounts/{account-id}
REST request to access the specific account information and entries history

#### Query Params
| param  | values | default | purpose                                                            |
|--------|--------|---------|--------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token for history (see Conventions → Pagination)         | 
| limit  | Number | 25      | Specify the amount of history items to return (1..100, clamped)     |

#### Response Body

Example response body looks as follows:
```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"group": "equity",
		"name": "Opening Balance",
		"money": {
			"amount": "10000.00",
			"currency": "USD"
		},
		"history": [
			{
				"title": "Acme Corp Salary",
				"debit": true,
				"created_at": "2026-08-12T11:51:00-05:00",
				"source_transaction": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"icon": "💼",
				"money": {
					"amount": "200.00",
					"currency": "USD"
				}
			}
		]
	},
	"meta": {
		"history": {
			"limit": 1,
			"total": 4,
			"next_cursor": "Y3Vyc29yOnYxOjE3NjcyMjU4NjA6MTY2NWI2MGU",
			"prev_cursor": null
		}
	}
}
```

## Transactions
Transactions are user-defined money operations. They reflect any user's operations over its WALLETS (not accounts).

A transaction describes exactly ONE money flow: an amount, a currency, a direction, and a wallet.
That is the whole user-facing model. The double-entry `postings` behind it are derived at the
backend by AI and are read-only everywhere in this API — see GET /transactions/{transaction-id}.

Two consequences worth stating up front:
- A transaction cannot be internally unbalanced, so no endpoint here rejects one for that reason;
- A movement BETWEEN two wallets is not a single transaction. It is a chain of two — see
  POST /transactions/chains, which is how transfers are expressed;

Adjustment transactions (a transaction that edits another's value) are planned but NOT part of this
revision. See [API_DEVELOPMENT.md](./API_DEVELOPMENT.md).

### GET /transactions
REST request to access the transactions overview list

#### Query Params
| param  | values | default | purpose                                                            |
|--------|--------|---------|--------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token for history (see Conventions → Pagination)         | 
| limit  | Number | 25      | Specify the amount of history items to return (1..100, clamped)     |

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Groceries store",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"money": {
				"amount": "90",
				"currency": "JPY"
			},
			"type": "expense",
			"origin": "manual",
			"wallet": {
				"name": "Random Credit Card",
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			},
			"category": null,
			"chain_id": null
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Groceries store",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"money": {
				"amount": "90",
				"currency": "JPY"
			},
			"type": "expense",
			"origin": "manual",
			"wallet": {
				"name": "Random Credit Card",
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			},
			"category": null,
			"chain_id": null
		}
	],
	"meta": {
		"limit": 25,
		"total": 18,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- This endpoint takes NO filters by design. It is the plain reverse-chronological feed. Anything
  narrower — a date range, a wallet, an amount band — goes through POST /transactions/search;
- `chain_id` is the id of the chain that created the transaction, or `null` for a standalone one.
  Both legs of a transfer carry the same value, which is how the two are related to each other —
  see POST /transactions/chains;
- Ordered `created_at DESC, chain_id ASC NULLS LAST, id DESC`. Chain members share a commit
  timestamp, so a transfer's legs arrive contiguously instead of interleaved with unrelated
  transactions from the same instant. They may still fall either side of a page boundary;
- There is no endpoint that reads a chain by id. To fetch one, filter
  `POST /transactions/search` on `chain_id`;

### GET /transactions/{transaction-id}
REST request to access the transaction details by its id

#### Query Params
| param  | values | default | purpose                                                             |
|--------|--------|---------|---------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token for postings (see Conventions → Pagination)        | 
| limit  | Number | 25      | Specify the amount of postings to return (1..100, clamped)          |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "Groceries store",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"money": {
			"amount": "90",
			"currency": "JPY"
		},
		"type": "expense",
		"origin": "manual",
		"wallet": {
			"name": "Random Credit Card",
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
		},
		"category": null,
		"chain_id": null,
		"evidence": null,
		"postings": [
			{
				"title": "Groceries",
				"debit": true,
				"created_at": "2026-08-12T11:51:00-05:00",
				"source_transaction": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"icon": "🛒",
				"money": {
					"amount": "200.00",
					"currency": "USD"
				}
			},
			{
				"title": "Random Credit Card",
				"debit": false,
				"created_at": "2026-08-12T11:51:00-05:00",
				"source_transaction": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"icon": "💳",
				"money": {
					"amount": "200.00",
					"currency": "EUR"
				}
			}
		],
		"analysis": {
			"balanced": false,
			"comment": "Currency mismatch. Debit is dispatched in USD while credit's currency is EUR"
		}
	},
	"meta": {
		"postings": {
			"limit": 25,
			"total": 2,
			"next_cursor": null,
			"prev_cursor": null
		}
	}
}
```
NOTES:
- `evidence` points at uploaded media and may be null. The endpoint that produces the URL is not yet
  specified — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- `postings` are GENERATED at the backend by AI and are strictly read-only. There is no way to
  author them, and no request body in this document accepts them. A transaction states a single
  money flow; deriving the double-entry legs from it is the backend's job;
- `icon` is a display glyph shown beside the posting, nothing more. It was previously called `emoji`
  and carried `"DR"` / `"CR"`, which duplicated `debit` — the side is `debit`, the icon is decoration;
- Because a transaction carries one flow and one amount, it CANNOT be unbalanced by construction.
  There is no `transaction_unbalanced` error, and `POST /transactions` never rejects a request on
  those grounds;
- `data.analysis` therefore reports on the GENERATED postings, not on user input. `balanced: false`
  means the backend could not derive a clean double-entry pair — most often because the two legs
  landed in different currencies — and `comment` explains why. It is a diagnostic surfaced to the
  user, never an error;

### POST /transactions/search
REST request to access the filtered, sorted, and paginated transactions with request body

#### Query Params
| param  | values   | default | purpose                                                            |
|--------|----------|---------|---------------------------------------------------------------------|
| order  | ASC/DESC | DESC    | order transactions based on created_at date                        |
| cursor | String   | absent  | Opaque page token (see Conventions → Pagination)                   |
| limit  | Number   | 25      | Specify the amount of results to return (1..100, clamped)          |

#### Request Body
Example of request body:
```json
{
	"filter_body": {
		"and": [
			{ "field_name": "id", "operator": "eq", "value": "1665b60e-bb7a-4360-8aa6-c1a578d81077" },
			{ "field_name": "created_at", "operator": "gte", "value": "2026-08-12T11:51:00-05:00" }
		]
	}
}
```

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Groceries store",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"money": {
				"amount": "90",
				"currency": "JPY"
			},
			"type": "expense",
			"origin": "manual",
			"wallet": {
				"name": "Random Credit Card",
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			},
			"category": null,
			"chain_id": null
		}
	],
	"meta": {
		"limit": 25,
		"total": 1,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- Currently only general sorting is supported (no per-leaf sorting). In the future per-leaf
  sorting will be supported
- Returns 200, not 201 — it creates nothing;
- Legal fields and operators are listed under Conventions → Filtering. An unknown `field_name` or a
  disallowed `operator` fails with 422 `validation_failed` and points at the offending leaf via
  `details[].field`;
- Cancelled transactions are EXCLUDED, matching the DELETE contract;

### PATCH /transactions/{transaction-id}
REST request to handle partial update of the transaction its id

#### Query Params
No query params are supported

#### Request Body
Example request body looks as follows:

```json
{
	"name": "New Name",
	"category": "Some Category",
	"evidence": {
		"url": "https://localhost:3002/media/some-evidence.jpg"
	}
}
```

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Name",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"money": {
			"amount": "90",
			"currency": "JPY"
		},
		"type": "expense",
		"origin": "manual",
		"wallet": {
			"name": "Random Credit Card",
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
		},
		"category": "Some Category",
		"chain_id": null
	},
	"meta": {}
}
```
NOTES:
- The response is the PREVIEW shape — the same object a `GET /transactions` list item carries. It
  does NOT include `evidence`, `postings`, or `analysis`, even though the request may have set
  `evidence`. Re-read the detail endpoint when those are needed;
- PATCH never touches money, and postings are backend-generated, so neither can be changed here.
  Editing `category` or `name` does not re-run posting generation;

### POST /transactions
REST request to create a new transaction

#### Query Params
No query params are supported

#### Headers
| header          | required | purpose                                                         |
|-----------------|----------|------------------------------------------------------------------|
| Idempotency-Key | yes      | UUID v4 guarding against duplicate creation. See Conventions      |

#### Request Body
Example request body looks as follows:

```json
{
	"name": "New Name",
	"currency": "RUB",
	"amount": "50.00",
	"wallet_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
	"origin": "manual",
	"type": "expense",
	"category": "Some Category",
	"evidence": {
		"url": "https://localhost:3002/media/some-evidence.jpg"
	}
}
```

#### Response Body
Returns 201 on creation. Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Name",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"money": {
			"amount": "50.00",
			"currency": "RUB"
		},
		"type": "expense",
		"origin": "manual",
		"wallet": {
			"name": "Random Credit Card",
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
		},
		"category": "Some Category",
		"chain_id": null
	},
	"meta": {
		"idempotent_replay": false
	}
}
```
NOTES:
- `evidence` points at uploaded media and may be null. The endpoint that produces the URL is not yet
  specified — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- The request body spells the money amount as a flat `amount` + `currency` pair rather than a nested
  `money` object, because the client sends what the user typed. Responses always nest it;
- `amount` is a decimal string here as everywhere. The request may under-specify the scale — `"50"`
  for RUB is accepted and read as `"50.00"` — but may not exceed it. Sending a JSON `50` instead of
  `"50"` fails with 422 / `amount_malformed`;
- Replays return 200 with `meta.idempotent_replay: true` and the originally created resource;
- Posting against a soft-deleted wallet fails with 409 `wallet_closed`;

### DELETE /transactions/{transaction-id}
REST request to cancel the transaction (soft delete)

#### Query Params
No query params are supported

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Name",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": "2026-08-12T11:51:00-05:00",
		"money": {
			"amount": "50.00",
			"currency": "RUB"
		},
		"type": "expense",
		"origin": "manual",
		"wallet": {
			"name": "Random Credit Card",
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
		},
		"category": "Some Category",
		"chain_id": null
	},
	"meta": {}
}
```
NOTES:
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- Repeating the call on an already-cancelled transaction returns 200 with the same body. It does not
  raise `already_deleted`;

### POST /transactions/chains
REST request to create multiple transactions at once. Difference from calling simple POST multiple times
is that if any of the transactions in chain is not created then all of them will be discarded (ACID).
Also, transactions will be bounded and the entire chain could be deleted in the future.

**This is how transfers are expressed.** A transaction carries one money flow, so moving money
between two wallets is two transactions — an `expense` on the source and an `income` on the
destination — submitted as one chain. Because the chain is atomic, money is never observed as having
left one wallet without arriving in the other.

For a CROSS-CURRENCY transfer the two entries simply carry different `currency` values. The exchange
rate is whatever applied at the moment the operation was committed: the amounts are fixed into the
chain at creation and are never recomputed. A transfer executed today reads the same next year, no
matter where rates move afterwards. Clients that want to show the rate to the user call
GET /currencies/convert first, then submit the figures it returned.

#### Query Params
No query params are supported

#### Headers
| header          | required | purpose                                                              |
|-----------------|----------|-----------------------------------------------------------------------|
| Idempotency-Key | yes      | UUID v4 guarding against duplicate creation of the whole chain        |

#### Request Body
Example request body looks as follows:

```json
{
	"transactions": [
		{
			"temporary_id": "transaction-1",
			"after": null,
			"name": "Expense Transaction",
			"currency": "RUB",
			"amount": "50.00",
			"wallet_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"origin": "manual",
			"type": "expense",
			"category": "Some Category",
			"evidence": {
				"url": "https://localhost:3002/media/some-evidence.jpg"
			}
		},
		{
			"temporary_id": "transaction-2",
			"after": "transaction-1",
			"name": "Income Transaction",
			"currency": "RUB",
			"amount": "50.00",
			"wallet_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"origin": "manual",
			"type": "income",
			"category": "Some Category",
			"evidence": {
				"url": "https://localhost:3002/media/some-evidence.jpg"
			}
		}
	]
}
```

#### Response Body
Returns 201 on creation. Example response body looks as follows:

```json
{
	"data": {
		"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"transactions": [
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Expense Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": null,
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "expense",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			},
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Income Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": null,
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "income",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			}
		]
	},
	"meta": {
		"idempotent_replay": false,
		"transactions": {
			"limit": 25,
			"total": 2,
			"next_cursor": null,
			"prev_cursor": null
		}
	}
}
```
NOTES:
- `evidence` points at uploaded media and may be null. The endpoint that produces the URL is not yet
  specified — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- `data` is an object, not an array, because the chain itself is the created resource. The nested
  `transactions` array is paginated through `meta.transactions` like any other embedded collection;
- The endpoint is all-or-nothing. A failure anywhere rolls the whole chain back, no `chain_id` is
  issued, and `error.details[].field` points at the failing entry by index (`transactions[1].amount`);
- `after` values reference `temporary_id`s within the same request. A cycle fails with 422
  `chain_cycle`, an unknown reference with 422 `chain_unknown_reference`;
- The idempotency key covers the entire chain, not the individual transactions inside it;
- A chain carries at most 100 entries, matching the pagination cap. More fails with 422
  `chain_too_long`. The whole chain runs in one transaction, so the bound keeps the lock window
  and the rollback cost predictable;

### DELETE /transactions/chains/{chain-id}
REST request to delete all the transactions in the chain (cancel entire chain) by chain id.

#### Query Params
No query params are supported

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"transactions": [
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Expense Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": "2026-08-12T11:51:00-05:00",
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "expense",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			},
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Income Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": "2026-08-12T11:51:00-05:00",
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "income",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
			}
		]
	},
	"meta": {
		"transactions": {
			"limit": 25,
			"total": 2,
			"next_cursor": null,
			"prev_cursor": null
		}
	}
}
```
NOTES:
- `category` accepts ANY string today and may be null. It becomes a reference to a stored category
  later, at which point free-form values stop being accepted — see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- Cancelling an already-cancelled chain returns 200 with the same body;

## Wallets
Wallets are used to store and operate real-world money storages, such as cash, credit cards, investment accounts.

### GET /wallets
REST request to get list of wallets the user have

#### Query Params
| param  | values | default | purpose                                                                   |
|--------|--------|---------|---------------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token (see Conventions → Pagination)                          | 
| limit  | Number | 25      | Specify the amount of wallet items to return (1..100, clamped)            |

#### Response Body
Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Random Credit Card",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"category": "Savings",
			"currency": "RUB",
			"money": {
				"amount": "50.00",
				"currency": "RUB"
			},
			"zero_balance": {
				"amount": "100.00",
				"currency": "RUB"
			},
			"favorite": true,
			"color": "#FF0000"
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Random Credit Card",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"category": "Savings",
			"currency": "RUB",
			"money": {
				"amount": "50.00",
				"currency": "RUB"
			},
			"zero_balance": {
				"amount": "100.00",
				"currency": "RUB"
			},
			"favorite": false,
			"color": "#FF0000"
		}
	],
	"meta": {
		"limit": 25,
		"total": 9,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- Favorite wallets always go first. `favorite` is the leading sort key, so the full ordering is
  `favorite DESC, created_at DESC, id DESC`;
- Favorites lead the RESULTS, they do not bypass filtering. On POST /wallets/search a favorite that
  does not match the filter is absent like any other non-match; the favorites that do match simply
  come first;

### POST /wallets
REST request to create new user's wallet

#### Query Params
_No query params supported_

#### Headers
| header          | required | purpose                                                      |
|-----------------|----------|---------------------------------------------------------------|
| Idempotency-Key | no       | UUID v4. Honoured when supplied. See Conventions              |

#### Request Body
Example request body looks as follows:

```json
{
	"name": "New Card",
	"color": "#FF0000",
	"opening_balance": "50.00",
	"zero_balance": "100.00",
	"currency": "USD",
	"category": "Savings"
}
```

#### Response Body
Returns 201 on creation. Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Card",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"category": "Savings",
		"currency": "USD",
		"money": {
			"amount": "50.00",
			"currency": "USD"
		},
		"zero_balance": {
			"amount": "100.00",
			"currency": "USD"
		},
		"favorite": false,
		"color": "#FF0000"
	},
	"meta": {
		"idempotent_replay": false
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- `money.currency` always equals the wallet's `currency`. The duplication is kept so the money object
  stays self-describing and can be rendered without the parent;
- `opening_balance` and `zero_balance` are flat decimal strings in the request, taking their currency
  from the sibling `currency` field. In responses `zero_balance` is a full money object like every
  other monetary value;

### GET /wallets/{wallet-id}
REST request to get details on the wallet by its id.

#### Query Params
| param  | values | default | purpose                                                                        |
|--------|--------|---------|---------------------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token for recent transactions (see Conventions → Pagination)        | 
| limit  | Number | 25      | Specify the amount of recent transactions to return (1..100, clamped)           |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Card",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": "2026-08-12T11:51:00-05:00",
		"deleted_at": null,
		"category": "Savings",
		"currency": "USD",
		"money": {
			"amount": "50.00",
			"currency": "USD"
		},
		"zero_balance": {
			"amount": "100.00",
			"currency": "USD"
		},
		"favorite": false,
		"color": "#FF0000",
		"last_month": {
			"inflow": {
				"amount": "0.00",
				"currency": "USD"
			},
			"outflow": {
				"amount": "0.00",
				"currency": "USD"
			}
		},
		"recent": [
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Expense Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": null,
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "expense",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": null
			},
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Expense Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": null,
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "expense",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": null
			},
			{
				"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"name": "Expense Transaction",
				"created_at": "2026-08-12T11:51:00-05:00",
				"updated_at": null,
				"deleted_at": null,
				"money": {
					"amount": "50.00",
					"currency": "RUB"
				},
				"type": "expense",
				"origin": "manual",
				"wallet": {
					"name": "Random Credit Card",
					"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077"
				},
				"category": "Some Category",
				"chain_id": null
			}
		]
	},
	"meta": {
		"recent": {
			"limit": 3,
			"total": 10,
			"next_cursor": "Y3Vyc29yOnYxOjE3NjcyMjU4NjA6MTY2NWI2MGU",
			"prev_cursor": null
		}
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- The namespaced meta key is `recent`, matching the field it paginates. It was previously called
  `transactions`, which did not match anything in `data`;
- `last_month.inflow` / `last_month.outflow` are money objects like everywhere else, not bare numbers;
- `last_month` is the only window in this document whose boundaries the server chooses rather than
  the client. It is a calendar month in the user's `timezone` preference, not a rolling 30 days, and
  not UTC. A user in `Europe/Warsaw` and a user in `America/Chicago` looking at the same wallet on
  the first of the month therefore see different figures, which is correct;
- The amounts are in the WALLET's currency, not the reporting currency. This is wallet detail, not
  Metrics — nothing here is converted;

### PATCH /wallets/{wallet-id}
REST request to perform partial update of wallet details.

#### Query Params
_No query params supported_

#### Request Body
Example request body looks as follows:
```json
{
	"name": "New Card",
	"favorite": false,
	"category": "Savings",
	"zero_balance": "100.00",
	"color": "#FF0000"
}
```

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Card",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": "2026-08-12T11:51:00-05:00",
		"deleted_at": null,
		"category": "Savings",
		"currency": "USD",
		"money": {
			"amount": "50.00",
			"currency": "USD"
		},
		"zero_balance": {
			"amount": "100.00",
			"currency": "USD"
		},
		"favorite": false,
		"color": "#FF0000"
	},
	"meta": {}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;

### DELETE /wallets/{wallet-id}
REST request to 'close' wallet. Related transactions are still accessible and wallet continue its existence
but is no longer displayed in lists or search.

#### Query Params
_No query params supported_

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "New Card",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": "2026-08-12T11:51:00-05:00",
		"deleted_at": "2026-08-12T11:51:00-05:00",
		"category": "Savings",
		"currency": "USD",
		"money": {
			"amount": "0.00",
			"currency": "USD"
		},
		"zero_balance": {
			"amount": "100.00",
			"currency": "USD"
		},
		"favorite": false,
		"color": "#FF0000"
	},
	"meta": {}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- Closing a wallet that still holds money fails with 409 `wallet_not_empty`. Move the balance out
  with POST /transactions first, then retry;
- Closing an already-closed wallet returns 200 with the same body;

### POST /wallets/search
REST request to access the filtered, sorted, and paginated wallets with request body

#### Query Params
| param  | values   | default | purpose                                                      |
|--------|----------|---------|---------------------------------------------------------------|
| order  | ASC/DESC | DESC    | order wallets based on created_at date                       |
| cursor | String   | absent  | Opaque page token (see Conventions → Pagination)             |
| limit  | Number   | 25      | Specify the amount of results to return (1..100, clamped)    |

#### Request Body
Example of request body:

```json
{
	"filter_body": {
		"and": [
			{ "field_name": "id", "operator": "eq", "value": "1665b60e-bb7a-4360-8aa6-c1a578d81077" },
			{ "field_name": "created_at", "operator": "gte", "value": "2026-08-12T11:51:00-05:00" }
		]
	}
}
```

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "New Card",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": "2026-08-12T11:51:00-05:00",
			"deleted_at": null,
			"category": "Savings",
			"currency": "USD",
			"money": {
				"amount": "50.00",
				"currency": "USD"
			},
			"zero_balance": {
				"amount": "100.00",
				"currency": "USD"
			},
			"favorite": false,
			"color": "#FF0000"
		}
	],
	"meta": {
		"limit": 25,
		"total": 1,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- Currently only general sorting is supported (no per-leaf sorting). In the future per-leaf
  sorting will be supported;
- Returns 200, not 201 — it creates nothing;
- Closed wallets are EXCLUDED. No result ever carries `deleted_at`, and there is no way to ask for
  them — matching the DELETE contract, which says a closed wallet leaves lists and search. An
  `include_deleted` flag is planned; see [API_DEVELOPMENT.md](./API_DEVELOPMENT.md);
- Legal fields and operators are listed under Conventions → Filtering;


## Goals
Goals are used as piggy-banks to track saving progress more efficiently and separate saved money from
those in turn.

A goal is a valid TARGET and SOURCE for transactions. Anywhere this document accepts a `wallet_id`,
a goal id is accepted too — funding a goal is an ordinary transfer chain (expense on a wallet,
income on the goal), and spending from one is the same chain reversed.

`progress` is never written directly. It is derived at the backend from the transactions touching
the goal, exactly the way a wallet's balance is. No endpoint in this document sets it, and there is
no contribution endpoint — POST /transactions/chains already covers the case.

### GET /goals
REST request to get list of goals the user have

#### Query Params
| param  | values | default | purpose                                                                 |
|--------|--------|---------|-------------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token (see Conventions → Pagination)                          | 
| limit  | Number | 25      | Specify the amount of goal items to return (1..100, clamped)            |

#### Response Body
Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Random Credit Card",
			"url": null,
			"currency": "RUB",
			"finish_at": "2026-08-12T11:51:00-05:00",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"target": {
				"amount": "50.00",
				"currency": "RUB"
			},
			"progress": {
				"amount": "30.00",
				"currency": "RUB"
			}
		},
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"name": "Random Credit Card",
			"url": null,
			"currency": "RUB",
			"finish_at": "2026-08-12T11:51:00-05:00",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"target": {
				"amount": "50.00",
				"currency": "RUB"
			},
			"progress": {
				"amount": "30.00",
				"currency": "RUB"
			}
		}
	],
	"meta": {
		"limit": 2,
		"total": 3,
		"next_cursor": "Y3Vyc29yOnYxOjE3NjcyMjU4NjA6MTY2NWI2MGU",
		"prev_cursor": null
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- URL field is always null. In the future it will be used to attach links to e-commerce sites;
- `currency` is the goal's own denomination, fixed at creation and never changed. `target` and
  `progress` are always expressed in it, so the two can never diverge;
- Ordered `created_at DESC, id DESC`. Goals do not sort by `finish_at` or by completion — a goal
  does not move in the list because its deadline approaches;
- Goals have NO `/search` endpoint, deliberately. The collection is small enough to page through,
  and every filter a client might want is cheap to apply over `GET /goals`. This is a decision, not
  an omission — do not add one by symmetry with wallets and transactions;

### POST /goals
REST request to create new user goal

#### Query Params
_No query params supported_

#### Headers
| header          | required | purpose                                          |
|-----------------|----------|---------------------------------------------------|
| Idempotency-Key | no       | UUID v4. Honoured when supplied. See Conventions  |

#### Request Body
Example request body looks as follows:

```json
{
	"name": "Random Credit Card",
	"finish_at": "2026-08-12T11:51:00-05:00",
	"currency": "RUB",
	"target": "50.00"
}
```

#### Response Body
Returns 201 on creation. Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "Random Credit Card",
		"url": null,
		"currency": "RUB",
		"finish_at": "2026-08-12T11:51:00-05:00",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"target": {
			"amount": "50.00",
			"currency": "RUB"
		},
		"progress": {
			"amount": "0.00",
			"currency": "RUB"
		}
	},
	"meta": {
		"idempotent_replay": false
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- URL field is always null. In the future it will be used to attach links to e-commerce sites;
- `target` is a flat decimal string in the request (paired with `currency`) and a money object in
  the response, following the same request/response asymmetry as POST /transactions;
- A freshly created goal always has zero `progress`;

### GET /goals/{goal-id}
REST request to get details on the goal by its id.

#### Query Params
| param  | values | default | purpose                                                            |
|--------|--------|---------|---------------------------------------------------------------------|
| cursor | String | absent  | Opaque page token for history (see Conventions → Pagination)         | 
| limit  | Number | 25      | Specify the amount of history items to return (1..100, clamped)     |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "Random Credit Card",
		"url": null,
		"currency": "RUB",
		"finish_at": "2026-08-12T11:51:00-05:00",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"target": {
			"amount": "50.00",
			"currency": "RUB"
		},
		"progress": {
			"amount": "30.00",
			"currency": "RUB"
		},
		"history": [
			{
				"title": "Goal Savings",
				"debit": true,
				"created_at": "2026-08-12T11:51:00-05:00",
				"source_transaction": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
				"icon": "💼",
				"money": {
					"amount": "30.00",
					"currency": "USD"
				}
			}
		]
	},
	"meta": {
		"history": {
			"limit": 3,
			"total": 1,
			"next_cursor": null,
			"prev_cursor": null
		}
	}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- URL field is always null. In the future it will be used to attach links to e-commerce sites;
- The endpoint previously declared no query params while returning history pagination meta. It
  paginates `history` exactly like GET /accounts/{account-id};

### PATCH /goals/{goal-id}
REST request to perform partial update of goal details.

#### Query Params
_No query params supported_

#### Request Body
Example request body looks as follows:
```json
{
	"name": "Random Credit Card",
	"finish_at": "2026-08-12T11:51:00-05:00",
	"target": "100.00"
}
```

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "Random Credit Card",
		"url": null,
		"currency": "RUB",
		"finish_at": "2026-08-12T11:51:00-05:00",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": null,
		"target": {
			"amount": "100.00",
			"currency": "RUB"
		},
		"progress": {
			"amount": "30.00",
			"currency": "RUB"
		}
	},
	"meta": {}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- URL field is always null. In the future it will be used to attach links to e-commerce sites;
- `progress` is not writable here or anywhere. It is recomputed at the backend from the goal's
  transactions, so it is echoed in the response but ignored if sent;

### DELETE /goals/{goal-id}
REST request to 'close' the goal. Related transactions are still accessible and goal continue its existence
but is no longer displayed in lists or search. Goal leftovers must be either transferred somewhere 
or the goal should be satisfied. The endpoint checks that `progress` is zero and refuses otherwise —
drain the goal with a POST /transactions/chains transfer first, the same way money moves anywhere else.

#### Query Params
_No query params supported_

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"name": "Random Credit Card",
		"url": null,
		"currency": "RUB",
		"finish_at": "2026-08-12T11:51:00-05:00",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"deleted_at": "2026-08-12T11:51:00-05:00",
		"target": {
			"amount": "100.00",
			"currency": "RUB"
		},
		"progress": {
			"amount": "0.00",
			"currency": "RUB"
		}
	},
	"meta": {}
}
```
NOTES:
- Currently, the 'goals' and 'wallets' are same API - separate them;
- URL field is always null. In the future it will be used to attach links to e-commerce sites;
- The zero-balance check failing raises 409 `goal_not_empty`. It is a 409 and not a 422 because the
  same request succeeds once the leftovers are moved;
- The section previously reused the DELETE /wallets/{wallet-id} heading;

## Currencies
Currencies are static entities (can't be added/modified) which are pulled from the backend
and reflect the country's currency in which money are counted.

### GET /currencies
REST request to get full list of currencies. Fetched at the app load

#### Query Params
No query params supported

#### Response Body
Example response body looks as follows:

```json
{
	"data": [
		{
			"code": "USD",
			"symbol": "$",
			"name": "USDollar",
			"decimals": 2
		},
		{
			"code": "EUR",
			"symbol": "€",
			"name": "Euro",
			"decimals": 2
		},
		{
			"code": "JPY",
			"symbol": "¥",
			"name": "Yen",
			"decimals": 0
		}
	],
	"meta": {
		"limit": null,
		"total": 40,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- The endpoint is not paginated. The currency table is small, static, and fetched once at app load,
  so the 25/100 page rules do not apply here and `meta.limit` is `null`;

### GET /currencies/convert
REST request to process conversion from one currency to another. 
Called on-spot at the moment of conversion (for example when cross-currency transfers are performed).

#### Query Params
| param     | values | default  | purpose                                                |
|-----------|--------|----------|--------------------------------------------------------|
| from_code | CUR    | required | code of the currency from which the value is converted |
| to_code   | CUR    | required | code of the currency to which value is converted       |
| amount    | String | required | decimal amount of from_code currency to convert        |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"from": {
			"amount": "100.00",
			"currency": "USD"
		},
		"to": {
			"amount": "8200.00",
			"currency": "RUB"
		},
		"rate": "82"
	},
	"meta": {
		"fetched_at": "2026-08-12T11:51:00-05:00"
	}
}
```
NOTES:
- `from` and `to` are ordinary money objects. The response previously spelled the `to` side as
  `to_code` / `to_value`, repeating the prefix inside the object;
- `fetched_at` describes the rate's freshness, not the conversion result, so it belongs in `meta`;
- An unknown code fails with 422 `unsupported_currency`. A known code with no usable rate fails with
  409 `rate_unavailable`;
- The `amount` query param is a decimal string like every other amount, sent as-is in the query
  string. It is validated against `from_code`'s scale, so `?amount=100.005&from_code=USD` fails with
  422 / `amount_precision`;
- `rate` is a string but is NOT money — it carries no currency and is not padded to any scale. `to`
  is the authoritative converted figure; clients render that rather than multiplying `rate`
  themselves, so rounding happens once, on the server;

### GET /currencies/rates/{currency-code}
REST request to get list of currency rates. Fetched at the app load and refetched each period of time 
or when main currency changes.

#### Query Params
| param     | values        | default | purpose                                                |
|-----------|---------------|---------|--------------------------------------------------------|
| target    | [CUR,CUR,CUR] | null    | Specify list of currencies which rates are interesting | 

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"base": "USD",
		"rates": {
			"RUB": "81.5",
			"USD": "1",
			"EUR": "0.9",
			"GBP": "100"
		}
	},
	"meta": {
		"fetched_at": "2026-08-12T11:51:00-05:00",
		"target": null
	}
}
```
NOTES:
- The path parameter is the base currency. The field is named `base` rather than `from` because
  nothing is being converted here — it is the denominator of every rate in the map;
- Rates are strings to avoid float rounding at the transport level;

## Metrics
Metrics are derived, read-only aggregations over accounts and transactions. Nothing here is
user-editable and every endpoint is safe to poll.

Every figure in this section is reported in the user's PREFERRED currency. Wallets, goals and
transactions may each be denominated differently; the backend converts them before aggregating, so a
metrics response never mixes currencies and the client never converts anything itself. The examples
below show USD because that is the example user's preference, not because it is a default.

That preference is not readable through this API and no query param overrides it — see Conventions →
User Preferences for where it lives and what happens when it is missing or invalid. There is
deliberately no `currency` param on these endpoints: a per-request override would be a second way to
choose the reporting currency, and the two would disagree the moment one of them was cached.

### GET /metrics/balance
REST request to access accumulated accounts data with balance and its state

#### Query Params
No query params are supported

#### Response Body

Example response body looks as follows:

```json
{
	"data": {
		"assets": {
			"amount": "10.00",
			"currency": "USD"
		},
		"liabilities": {
			"amount": "20.00",
			"currency": "USD"
		},
		"equity": {
			"amount": "-10.00",
			"currency": "USD"
		},
		"balanced": true,
		"comments": null
	},
	"meta": {}
}
```
NOTES:
- The metrics endpoints were previously nested under the Currencies section;

### GET /metrics/net-worth
REST request to calculate the total net worth and its diff for period of time.

#### Query Params
| param  | values   | default | purpose                              |
|--------|----------|---------|--------------------------------------|
| since  | Datetime | null    | Day-zero for calculations. `null` means all time |
| points | Number   | 10      | Amount of diff history series points |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"money": {
			"amount": "10.00",
			"currency": "USD"
		},
		"net_diff": {
			"percentage": 75,
			"direction": "up"
		},
		"series": [
			{
				"timestamp": "2026-08-12T11:51:00-05:00",
				"money": {
					"amount": "5.00",
					"currency": "USD"
				}
			},
			{
				"timestamp": "2026-08-12T11:51:00-05:00",
				"money": {
					"amount": "7.00",
					"currency": "USD"
				}
			},
			{
				"timestamp": "2026-08-12T11:51:00-05:00",
				"money": {
					"amount": "1.00",
					"currency": "USD"
				}
			}
		]
	},
	"meta": {
		"since": "2026-08-12T11:51:00-05:00",
		"points": 10
	}
}
```
NOTES:
- `series` is a fixed-size sampling controlled by `points`, not a paginated collection, so it gets
  no namespaced pagination triple in `meta`. `points` is an echoed request param;

### GET /metrics/cash-flow
REST request to calculate inflow, outflow, and the resulting net for a period of time.

#### Query Params
| param  | values   | default | purpose                           |
|--------|----------|---------|-----------------------------------|
| since  | Datetime | null    | Day-zero for calculations. `null` means all time |

#### Response Body
Example response body looks as follows:

```json
{
	"data": {
		"inflow": {
			"amount": "15.00",
			"currency": "USD"
		},
		"outflow": {
			"amount": "10.00",
			"currency": "USD"
		},
		"total_net": {
			"amount": "5.00",
			"currency": "USD"
		},
		"savings_rate": 15
	},
	"meta": {
		"since": "2026-08-12T11:51:00-05:00"
	}
}
```
NOTES:
- The description previously read "calculate the total net worth", copied from /metrics/net-worth;
- `savings_rate` is a percentage, not money, so it stays a bare number;

## Actions
The "needs action" queue: things the user must DECIDE about. An action is produced either by the
assistant (a recommendation) or by the scheduler (a time-triggered condition such as a subscription
charging tomorrow against a wallet that cannot cover it).

Every action is a different decision, but they are NOT different resources. The envelope below is
identical for all of them; what varies is the set of choices the server offers, carried as
`resolutions`. A client renders one button per resolution and never switches on the action's `kind`
to decide what the buttons say.

This is the whole point of the shape: the backend can introduce a new kind of action — a new AI
recommendation, a new scheduled check — and every existing client renders and resolves it correctly
with no release. A client that hardcodes labels per `kind` reintroduces exactly the coupling this
design removes.

An action is a DECISION, not a form. No resolution ever collects input beyond the choice itself. When
a decision needs data — which wallet to move money from — the client navigates to the flow that
already exists, using `subject` as the deep link, and the action is resolved or dismissed separately.
Field descriptors, embedded schemas and server-driven forms are deliberately absent and are not a
gap to fill later.

Actions have no `/search` endpoint and no detail endpoint. The queue is small, the list row carries
the entire resource, and there is nothing a detail view would add.

### GET /actions
REST request to access the pending action queue.

#### Query Params
| param    | values                                       | default   | purpose                                  |
|----------|----------------------------------------------|-----------|------------------------------------------|
| limit    | Number                                       | 25        | Page size, capped at 100                 |
| cursor   | String                                       | absent    | Keyset cursor                            |
| status   | `pending`, `resolved`, `dismissed`, `expired` | `pending` | Which queue state to list                |
| source   | `assistant`, `scheduler`                     | absent    | Restrict to one producer. Absent means both |
| severity | `info`, `warning`, `critical`                | absent    | Restrict to one severity                 |

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"source": "scheduler",
			"kind": "insufficient_funds",
			"severity": "critical",
			"status": "pending",
			"title": "Netflix charges tomorrow",
			"body": "Card has 4.20 USD available and the payment is 15.99 USD.",
			"subject": {
				"type": "wallet",
				"id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"
			},
			"money": {
				"amount": "15.99",
				"currency": "USD"
			},
			"group_key": "recurring:netflix:9a1e4c2b",
			"occurrences": 3,
			"last_seen_at": "2026-08-12T11:51:00-05:00",
			"expires_at": "2026-08-13T00:00:00-05:00",
			"resolved_at": null,
			"resolutions": [
				{
					"id": "top_up",
					"label": "Move money",
					"intent": "primary",
					"applies": false
				},
				{
					"id": "dismiss",
					"label": "Ignore",
					"intent": "secondary",
					"applies": false
				}
			]
		},
		{
			"id": "3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204",
			"created_at": "2026-08-12T09:14:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"source": "assistant",
			"kind": "uncategorized",
			"severity": "info",
			"status": "pending",
			"title": "3 transactions need a category",
			"body": "Purchases from last week look like groceries.",
			"subject": null,
			"money": {
				"amount": "142.30",
				"currency": "USD"
			},
			"group_key": null,
			"occurrences": 1,
			"last_seen_at": "2026-08-12T09:14:00-05:00",
			"expires_at": null,
			"resolved_at": null,
			"resolutions": [
				{
					"id": "apply",
					"label": "Categorise as Groceries",
					"intent": "primary",
					"applies": true
				},
				{
					"id": "review",
					"label": "Review",
					"intent": "secondary",
					"applies": false
				},
				{
					"id": "dismiss",
					"label": "Ignore",
					"intent": "secondary",
					"applies": false
				}
			]
		}
	],
	"meta": {
		"limit": 25,
		"total": 2,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- `kind` is deliberately NOT enumerated. It is an open vocabulary that grows whenever the assistant
  learns to recognise something new. Clients MAY use it to select an icon and MUST fall back to a
  generic icon for values they do not know. Clients must never derive labels, button counts or
  behaviour from it — that is what `resolutions` is for;
- `source` and `severity` ARE closed vocabularies and are listed in Enumerations. They are the
  API's own classification, not the assistant's;
- Both producers share one collection on purpose. Splitting assistant-produced and scheduler-produced
  actions into two endpoints would force the client to merge two independently ordered lists, which
  cannot be paginated by keyset — there is no single cursor over a merge;
- `subject` is a polymorphic reference — `{type, id}` — or `null` when the action is not about one
  resource. It is what the client deep-links to. `type` matches a resource name in this document;
- `money` is the amount at stake, in the currency of whatever the action concerns. It is NOT
  converted to the reporting currency; this is not Metrics. `null` when the action is not about an
  amount;
- `group_key` collapses recurring conditions. A scheduled check that fires daily until payday updates
  ONE row — bumping `occurrences` and `last_seen_at` — instead of appending a new action per run.
  `null` means the action does not recur. `occurrences` is 1 for a non-recurring action, never 0;
- `expires_at` is when the action stops being answerable — the charge date has passed. On expiry the
  server moves it to `status: "expired"`. `null` means it does not expire;
- `resolutions` is never empty. An action with nothing to choose is a notification, not an action;
- `resolutions[].intent` is a rendering hint (`primary`, `secondary`, `danger`), not behaviour. A
  client may style all of them identically;
- `resolutions[].applies` states whether choosing it changes OTHER resources. See
  POST /actions/{action-id}/resolve;
- Dismissal is a resolution like any other, not a DELETE. This lets the server decide per action
  whether ignoring it is even offered — a critical action may omit `dismiss` entirely — and keeps one
  code path for answering the queue;

### POST /actions/{action-id}/resolve
REST request to answer an action by choosing one of its offered resolutions.

#### Request Body

Example request body looks as follows:

```json
{
	"resolution_id": "apply"
}
```

#### Response Body

Returns the updated action in the same shape as one element of GET /actions.

```json
{
	"data": {
		"id": "3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204",
		"created_at": "2026-08-12T09:14:00-05:00",
		"updated_at": "2026-08-12T12:02:00-05:00",
		"deleted_at": null,
		"source": "assistant",
		"kind": "uncategorized",
		"severity": "info",
		"status": "resolved",
		"title": "3 transactions need a category",
		"body": "Purchases from last week look like groceries.",
		"subject": null,
		"money": {
			"amount": "142.30",
			"currency": "USD"
		},
		"group_key": null,
		"occurrences": 1,
		"last_seen_at": "2026-08-12T09:14:00-05:00",
		"expires_at": null,
		"resolved_at": "2026-08-12T12:02:00-05:00",
		"resolutions": []
	},
	"meta": {}
}
```
NOTES:
- `resolution_id` MUST be one of the ids offered on that action. Anything else fails with 422
  `unknown_resolution` — including an id that is valid on a different action;
- Choosing a resolution whose `applies` was `true` performs the described change to other resources
  as part of the same request. The response then carries `X-Write-Version`, so a client can send
  `Read-At-Least` on the follow-up read of whatever it touched. When `applies` was `false` nothing
  outside the action changes and no write version is emitted;
- `status` becomes `resolved` for every resolution except the one the server designates as dismissal,
  which produces `dismissed`. The distinction is recorded for analytics — "how often is this
  recommendation ignored" is not answerable if both collapse to one state;
- `resolutions` is emptied once answered. A resolved action offers no further choices, and an empty
  array rather than a stale list is what stops a client re-rendering buttons that no longer work;
- Resolving an already-resolved, dismissed or expired action fails with 409
  `action_already_resolved`. It is a conflict rather than a validation error because the request was
  well-formed and would have succeeded earlier;
- The header is OPTIONAL here per the Idempotency rules, but supplying `Idempotency-Key` is
  recommended for resolutions with `applies: true`, since those move real data;
- A resolved action is NOT soft-deleted. `deleted_at` stays `null` and `status` carries the queue
  state. The two are independent;

## Notifications
Things the user is TOLD. A notification reports something that already happened and needs no decision
— a transfer completed, a card approached its limit, salary landed.

This is the whole distinction from Actions: an action asks the user to CHOOSE and carries
`resolutions`; a notification carries none and is answered only by acknowledging it. One event may
produce both, and they stay separate resources.

Notifications are read-only to the client apart from acknowledgement. Nothing creates one through
this API — they are produced by the backend.

The slice has three REST endpoints plus one stream. The stream carries new notifications as they are
produced; the list carries everything that arrived before the client connected. Neither replaces the
other: a client fetches the list on mount and opens the stream for the live tail.

### GET /notifications
REST request to access the notification backlog.

#### Query Params
| param        | values                        | default | purpose                                    |
|--------------|-------------------------------|---------|--------------------------------------------|
| limit        | Number                        | 25      | Page size, capped at 100                   |
| cursor       | String                        | absent  | Keyset cursor                              |
| acknowledged | Bool                          | absent  | Restrict to read or unread. Absent means both |
| severity     | `info`, `warning`, `critical` | absent  | Restrict to one severity                   |

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"severity": "critical",
			"title": "Visa Credit near limit",
			"body": "You are at 82% of your 2,000.00 USD limit.",
			"subject": {
				"type": "wallet",
				"id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"
			},
			"acknowledged_at": null
		},
		{
			"id": "3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204",
			"created_at": "2026-08-12T10:04:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"severity": "info",
			"title": "Transfer completed",
			"body": "500.00 USD moved from Main Checking to Emergency Fund.",
			"subject": {
				"type": "transaction",
				"id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92"
			},
			"acknowledged_at": "2026-08-12T10:06:00-05:00"
		}
	],
	"meta": {
		"limit": 25,
		"total": 2,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- Ordering is the global default — `created_at DESC, id DESC`. Notifications add no leading sort key:
  unlike the Actions queue, this is a feed to be read rather than a list to be worked through, so a
  `critical` notification from Tuesday does NOT outrank an `info` from this morning;
- `acknowledged_at` is a timestamp, not a boolean. `null` means unread. This follows the same shape
  as `deleted_at` and `resolved_at` — the fact and its time are one field, not two;
- No relative time string is ever sent. `"8m"` and `"Yesterday"` are FORMATTING, computed by the
  client from `created_at` — they depend on the reader's locale and on when they happen to be
  looking, neither of which the server knows. See Conventions → User Preferences;
- `subject` is the same polymorphic `{type, id}` reference Actions uses, or `null`. It is what the
  client deep-links to when the notification is tapped;
- `severity` shares its vocabulary with the Actions `severity` field on purpose. Two adjacent slices
  with two near-identical urgency scales would be a permanent source of mapping bugs in the UI;
- Money inside `body` is already rendered into the sentence, because the sentence is what the backend
  generated. There is no money object on a notification and no client-side substitution to perform;

### GET /notifications/count
REST request to read how many notifications are unacknowledged.

It exists so the badge on the bell does not require walking the list. It is not paginated.

#### Query Params
No query params are supported

#### Response Body

Example response body looks as follows:

```json
{
	"data": {
		"unacknowledged": 3,
		"total": 41
	},
	"meta": {}
}
```
NOTES:
- `total` counts every notification the user has, acknowledged or not. `unacknowledged` is the badge;
- This value goes stale the moment the stream delivers a notification. Clients increment locally on
  arrival and treat this endpoint as the value at load time — refetching it per event would defeat
  the point of having a stream;

### POST /notifications/{notification-id}/ack
REST request to acknowledge a notification.

#### Request Body
No request body is required

#### Response Body

Returns the updated notification in the same shape as one element of GET /notifications.

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": "2026-08-12T12:02:00-05:00",
		"deleted_at": null,
		"severity": "critical",
		"title": "Visa Credit near limit",
		"body": "You are at 82% of your 2,000.00 USD limit.",
		"subject": {
			"type": "wallet",
			"id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"
		},
		"acknowledged_at": "2026-08-12T12:02:00-05:00"
	},
	"meta": {}
}
```
NOTES:
- Acknowledging is IDEMPOTENT by nature and needs no `Idempotency-Key`. Acknowledging an already
  acknowledged notification succeeds and returns it unchanged, keeping the original
  `acknowledged_at`. It is not a 409 — the caller's intent is already satisfied, and a double-tapped
  bell is not a conflict;
- There is no un-acknowledge. Marking something read again as unread is a feature nobody asked for
  and it would make `acknowledged_at` meaningless as a record of when the user saw it;
- Acknowledging emits `X-Write-Version` like any mutation, so a client that immediately refetches
  the count can send `Read-At-Least`;

### GET /notifications/stream
Server-Sent Events stream carrying notifications as they are produced.

**This endpoint is exempt from the Conventions in this document.** It returns `text/event-stream`,
not JSON, so there is no response envelope, no `data`/`meta` split, no pagination block and no
`meta.cached`. Those rules describe request/response pairs and a stream is not one. Every OTHER
convention still applies — authentication, rate limits, and error status codes on the initial
handshake.

The stream carries only what happens AFTER it is opened. It never replays the backlog; that is what
GET /notifications is for.

#### Query Params
No query params are supported

#### Response

```
event: notification.created
id: 1665b60e-bb7a-4360-8aa6-c1a578d81077
data: {"id":"1665b60e-bb7a-4360-8aa6-c1a578d81077","created_at":"2026-08-12T11:51:00-05:00","updated_at":null,"deleted_at":null,"severity":"critical","title":"Visa Credit near limit","body":"You are at 82% of your 2,000.00 USD limit.","subject":{"type":"wallet","id":"9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"},"acknowledged_at":null}

event: notification.acknowledged
id: 3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204
data: {"id":"3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204","acknowledged_at":"2026-08-12T12:02:00-05:00"}

: heartbeat
```

| event                      | payload                                    |
|----------------------------|--------------------------------------------|
| `notification.created`     | the complete notification, as in the list  |
| `notification.acknowledged`| `{id, acknowledged_at}` only               |

NOTES:
- `notification.created` carries the FULL resource, not just an id, so the client prepends it without
  a follow-up request. This is safe here specifically because a notification is display-only and
  nothing is derived from it. An event carrying a balance or any other projected figure would have to
  be thin — an id the client reads back — or it would race the read model and show a number the next
  read contradicts. See Consistency;
- `notification.acknowledged` exists so a second tab or another device does not keep showing an
  unread badge for something the user already dismissed. It is deliberately thin: the id and the new
  timestamp are the only things that changed;
- The SSE `id:` field is the notification id and doubles as the resume token. A client reconnecting
  sends `Last-Event-ID` and receives everything produced after it;
- Resume is BEST EFFORT and bounded by server-side retention. A client that has been disconnected
  long enough, or that never had an id to resume from, refetches GET /notifications instead of
  trusting the stream to backfill. Refetching the list is always correct and is the recommended
  reconnect path in every case;
- A comment line — `: heartbeat` — is sent at least every 30 seconds. Without it neither the client
  nor any intermediate proxy can distinguish an idle stream from a dead connection, and the
  connection is silently reaped;
- The stream is a READ. It emits no `X-Write-Version` and honours no `Read-At-Least`;
- Clients must tolerate unknown `event` values by ignoring them. Adding an event type is an ADDITIVE
  change under the versioning rules;

## Automations
User-authored rules: WHEN something matches, DO something. An automation is the only place in this
API where the user programs the backend, so its shape is deliberately narrow.

A rule has three parts:
- a TRIGGER, which says when the rule is evaluated and what it matches;
- a list of EFFECTS, which say what happens when it matches;
- an `enabled` flag, because turning a rule off must not mean deleting it;

The condition inside a trigger is the SAME `filter_body` tree used by the `/search` endpoints — same
group nodes, same leaf nodes, same operators, same per-resource field policies, same failure codes.
See Conventions → Filtering. This is the central decision of the slice: a rule condition and a search
query are the same question asked at different times, so they share one grammar, one validator, and
one UI builder. A second condition language would be a second thing to specify, secure and version.

Effects are NOT free-form. `effects[].type` is a closed vocabulary with documented params per member.
The API accepts no expression, script, or template string anywhere — an automation can only select
from things the backend already knows how to do.

NOTES:
- The field is `effects`, not `action`. "Action" is taken by the needs-action queue, and a rule that
  produced an `action` containing an `action` would be unreadable;
- Automations are FORWARD-ONLY. Creating or enabling a rule never touches existing data — it applies
  to what happens after it. Retroactive application is a separate, destructive operation and is not
  in this document;
- Rules evaluate in `created_at ASC` order, oldest first, and effects apply in that order. When two
  rules set the same field, the LAST one to run wins. This is stated so the outcome is predictable
  rather than incidental; explicit priority ordering is not supported;

### GET /automations
REST request to access the user's automation rules.

#### Query Params
| param   | values | default | purpose                                        |
|---------|--------|---------|------------------------------------------------|
| limit   | Number | 25      | Page size, capped at 100                       |
| cursor  | String | absent  | Keyset cursor                                  |
| enabled | Bool   | absent  | Restrict to enabled or disabled. Absent means both |

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"name": "Auto-categorise coffee shops",
			"icon": "tag",
			"enabled": true,
			"trigger": {
				"type": "event",
				"event": "transaction.created",
				"schedule": null,
				"filter_body": {
					"and": [
						{
							"field_name": "name",
							"operator": "icontains",
							"value": "coffee"
						},
						{
							"field_name": "amount",
							"operator": "lte",
							"value": "25.00"
						}
					]
				}
			},
			"effects": [
				{
					"type": "set_category",
					"params": {
						"category": "Dining"
					}
				}
			],
			"last_run_at": "2026-08-12T11:40:00-05:00",
			"runs": 14
		},
		{
			"id": "3f8c1a90-5b2e-4d66-8f01-7c9a3e5b1204",
			"created_at": "2026-08-10T08:00:00-05:00",
			"updated_at": null,
			"deleted_at": null,
			"name": "Monthly savings sweep",
			"icon": "transfer",
			"enabled": false,
			"trigger": {
				"type": "schedule",
				"event": null,
				"schedule": "monthly",
				"filter_body": null
			},
			"effects": [
				{
					"type": "transfer",
					"params": {
						"from_wallet_id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
						"to_wallet_id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
						"money": {
							"amount": "200.00",
							"currency": "USD"
						}
					}
				},
				{
					"type": "notify",
					"params": {
						"severity": "info",
						"title": "Savings sweep ran"
					}
				}
			],
			"last_run_at": null,
			"runs": 0
		}
	],
	"meta": {
		"limit": 25,
		"total": 2,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- The list returns the COMPLETE resource, not a preview. A rule is small and the browser renders its
  condition inline, so a detail request would fetch nothing new. GET /automations/{automation-id}
  exists for reading one by id, and returns the identical shape;
- Ordering is the global default — `created_at DESC, id DESC`. Note this is the REVERSE of evaluation
  order: the list shows newest first because that is how the user thinks about their rules, while the
  engine runs oldest first so that later rules can override earlier ones;
- `trigger.event` and `trigger.schedule` are both always present, and exactly one is non-`null`,
  selected by `trigger.type`. Following the Timestamps rule, the inapplicable one is `null` rather
  than an omitted key, so a client reads `trigger.schedule` without guarding;
- `trigger.filter_body` is `null` for an unconditional rule. `null` means "always", which is why an
  empty group is rejected instead of meaning the same thing — see Conventions → Filtering;
- The field policy applied to `filter_body` is the one belonging to the trigger's SUBJECT resource. A
  `transaction.created` trigger validates against the transactions policy. A `schedule` trigger with
  a filter validates against wallets, since a scheduled rule scans wallets;
- `icon` is a free-form string with a client-side registry and a documented fallback, exactly like
  action `kind`. The server never validates it against a list of known icons;
- `last_run_at` and `runs` are read-only counters maintained by the engine. `runs` counts MATCHES
  that applied effects, not evaluations — a rule checked a thousand times that never matched reports
  `0`. Without this a rule that silently stopped matching is indistinguishable from one that works;

### POST /automations
REST request to create an automation rule.

#### Request Body

Example request body looks as follows:

```json
{
	"name": "Auto-categorise coffee shops",
	"icon": "tag",
	"enabled": true,
	"trigger": {
		"type": "event",
		"event": "transaction.created",
		"filter_body": {
			"and": [
				{
					"field_name": "name",
					"operator": "icontains",
					"value": "coffee"
				}
			]
		}
	},
	"effects": [
		{
			"type": "set_category",
			"params": {
				"category": "Dining"
			}
		}
	]
}
```

#### Response Body

Returns the created rule in the same shape as one element of GET /automations, with 201.

NOTES:
- `enabled` defaults to `true` when omitted. A rule created disabled is legitimate — building it in
  parts before switching it on — but the common case is wanting it to work;
- `trigger.schedule` is omitted rather than sent as `null` when `type` is `event`, and vice versa.
  Sending the one that does not belong to the declared `type` fails with 422 `validation_failed` and
  detail code `trigger_field_conflict`. Responses always include both keys; requests supply one;
- `effects` must contain at least one entry. A rule with no effects matches and does nothing, which
  is never what the user meant;
- `Idempotency-Key` is optional here per the Idempotency rules, but recommended: a double-submitted
  form otherwise creates two identical rules that both run;

### GET /automations/{automation-id}
REST request to access a single automation rule.

#### Response Body

Returns the same shape as one element of GET /automations, wrapped as a single object.

### PATCH /automations/{automation-id}
REST request to perform a partial update of an automation rule, including enabling and disabling it.

#### Request Body

Example request body looks as follows:

```json
{
	"enabled": false
}
```

#### Response Body

Returns the updated rule in the same shape as one element of GET /automations.

NOTES:
- There is deliberately NO `POST /automations/{automation-id}/toggle`. Enabling is setting a field,
  `PATCH` already sets fields, and a dedicated endpoint that flips a boolean rather than setting it
  is not idempotent — two retries of the same "toggle" leave the rule where it started;
- `trigger` and `effects` are replaced WHOLE when supplied, never merged. Deep-merging a condition
  tree has no sane definition — there is no way to say "change the third leaf" — so a client editing
  a condition sends the complete new `trigger`;
- Editing a rule does not re-run it, and does not undo what its previous version did. Effects already
  applied stay applied;

### DELETE /automations/{automation-id}
REST request to delete an automation rule.

#### Response Body

Returns the soft-deleted rule in the same shape as one element of GET /automations.

NOTES:
- Deletion is a soft delete, setting `deleted_at`. A deleted rule stops evaluating immediately;
- Nothing a rule already did is reverted. Transactions it categorised keep their category and
  transfers it made stay made — the rule is deleted, not its history;
- Disabling is preferable to deleting for a rule the user may want back, which is why `enabled`
  exists as a separate concept from `deleted_at`;

### Effect Types
`effects[].type` is a closed vocabulary. Each member documents its own `params` object, and no other
keys are accepted inside it.

| type           | params                                            | does                                      |
|----------------|---------------------------------------------------|-------------------------------------------|
| `set_category` | `category` (String)                               | sets the matched transaction's category   |
| `notify`       | `severity`, `title`                               | raises a notification                     |
| `raise_action` | `severity`, `title`, `body`                       | puts an item in the needs-action queue    |
| `transfer`     | `from_wallet_id`, `to_wallet_id`, `money`         | creates a transfer chain between wallets  |

NOTES:
- `set_category` is only valid on a trigger whose subject is a transaction. An effect that cannot
  apply to the trigger's subject fails at CREATE time with 422 `validation_failed` and detail code
  `effect_subject_mismatch`, not silently at run time;
- `transfer` creates an ordinary transaction chain, identical to POST /transactions/chains. It is
  subject to every rule that applies there, including a closed target wallet failing the run;
- `raise_action` produces an action with `source: "scheduler"`. Its `resolutions` are supplied by the
  backend, not by the rule — a user-authored rule cannot define the choices offered to the user,
  because that would make `resolutions` a free-form structure and reintroduce server-driven forms;
- Adding a member to this table is an ADDITIVE change. Clients must tolerate an effect type they do
  not recognise and render it generically rather than failing the whole rule;
- A run that fails partway does NOT roll back earlier effects in the same rule. Effects are applied
  in order and each is its own operation; there is no transaction across them;

## Webhooks
Outbound HTTP callbacks. The user registers an endpoint, subscribes it to event types, and the
backend POSTs to that URL when those events occur.

This slice is unusual in one respect: most of it describes what the API SENDS rather than what it
returns. The request the user's server receives — its headers, its signature, its retry behaviour —
is as much a contract as any response here, and is specified under Delivery below.

A webhook has three moving parts:
- the ENDPOINT: a url, a title, a secret, and whether it is enabled;
- its SUBSCRIPTIONS: which event types it wants, each its own addressable resource;
- its DELIVERIES: the log of what was actually sent and what came back;

### GET /webhooks
REST request to access the user's registered endpoints.

#### Query Params
| param   | values | default | purpose                                        |
|---------|--------|---------|------------------------------------------------|
| limit   | Number | 25      | Page size, capped at 100                       |
| cursor  | String | absent  | Keyset cursor                                  |
| enabled | Bool   | absent  | Restrict to enabled or disabled. Absent means both |

#### Response Body

Example response body looks as follows:

```json
{
	"data": [
		{
			"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": null,
			"title": "Ledger sync",
			"url": "https://hooks.example.com/finance/ledger",
			"enabled": true
		}
	],
	"meta": {
		"limit": 25,
		"total": 1,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- The `secret` is NEVER present here, or on any read. It is returned exactly twice in an endpoint's
  life: when it is created, and when it is rotated. If the user loses it they rotate — there is no
  endpoint that reveals it again, and adding one would turn a read-only leak into a credential leak;
- There is no `deleted_at`. Webhooks are HARD deleted, unlike every other resource in this document.
  A deleted endpoint must stop receiving immediately and unambiguously, and there is no user-facing
  history to preserve — the delivery log is separate and outlives the endpoint;
- `enabled` is the pause switch. A disabled endpoint keeps its subscriptions and its secret and
  receives nothing;

### POST /webhooks
REST request to register an endpoint.

#### Request Body

```json
{
	"title": "Ledger sync",
	"url": "https://hooks.example.com/finance/ledger",
	"enabled": true
}
```

#### Response Body

Returns the endpoint WITH its secret, and 201. This is one of only two responses in the API that
contain the secret.

```json
{
	"data": {
		"id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
		"created_at": "2026-08-12T11:51:00-05:00",
		"updated_at": null,
		"title": "Ledger sync",
		"url": "https://hooks.example.com/finance/ledger",
		"enabled": true,
		"secret": "whsec_9f2b1c7e4a8d6350bb19e0f4c2a7d183"
	},
	"meta": {}
}
```
NOTES:
- `url` must be absolute and use `http` or `https`. It is additionally checked at DELIVERY time
  against the address guard described under Delivery, so a URL that resolves to a private address is
  accepted here and fails when sent. Validation at registration cannot be authoritative — DNS can
  change between registration and delivery;
- A new endpoint has NO subscriptions and therefore receives nothing. Subscribing is a separate call;
- `enabled` defaults to `true`;

### GET /webhooks/{webhook-id}
REST request to access a single endpoint. Returns the same shape as one element of GET /webhooks,
without the secret.

### PATCH /webhooks/{webhook-id}
REST request to partially update an endpoint — its `title`, `url`, or `enabled` flag.

Returns the updated endpoint, without the secret.

NOTES:
- Changing `url` does NOT rotate the secret, and does not re-verify anything. The same secret now
  signs requests to a different host, which is the user's decision to make;
- Subscriptions are not editable here. They are their own sub-resource;

### DELETE /webhooks/{webhook-id}
REST request to delete an endpoint.

Deletion is permanent and cascades to the endpoint's subscriptions. Pending deliveries for that
endpoint are abandoned. The delivery log is retained.

### POST /webhooks/{webhook-id}/secret
REST request to rotate an endpoint's signing secret.

#### Request Body
No request body is required

#### Response Body

Returns the endpoint with the NEW secret, in the same shape as POST /webhooks.

NOTES:
- Rotation is the only recovery path for a lost or leaked secret;
- The previous secret remains valid for a GRACE PERIOD of 24 hours, during which deliveries are
  signed with the new secret but the old one is still considered valid by the endpoint owner's
  verification. Without a window, rotation breaks every in-flight and in-progress delivery the
  instant it is called, and the user's receiver rejects real traffic until they redeploy;
- Rotating twice inside the grace period invalidates the oldest secret immediately. Only two secrets
  are ever live at once;

### GET /webhooks/event-types
REST request to access the catalog of subscribable event types.

This is the source the subscription UI populates from. It is not a static list in client code — a new
event type becomes subscribable the moment the backend publishes it here.

#### Query Params
No query params are supported

#### Response Body

```json
{
	"data": [
		{
			"event": "transaction.created",
			"subject": "transaction",
			"description": "A transaction was recorded."
		},
		{
			"event": "transaction.updated",
			"subject": "transaction",
			"description": "An existing transaction changed."
		},
		{
			"event": "transaction.deleted",
			"subject": "transaction",
			"description": "A transaction was cancelled."
		},
		{
			"event": "wallet.created",
			"subject": "wallet",
			"description": "A wallet was opened."
		},
		{
			"event": "wallet.updated",
			"subject": "wallet",
			"description": "A wallet's details or balance changed."
		},
		{
			"event": "goal.reached",
			"subject": "goal",
			"description": "A goal's progress met its target."
		}
	],
	"meta": {
		"limit": null,
		"total": 6,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- Not paginated. The catalog is small, fixed at any given moment, and always returned complete —
  `limit` is `null` per the Non-Paginated Endpoints rule;
- `event` is the value used in a subscription and sent in the `X-Webhook-Event` header;
- `subject` names the resource the payload's `data` will contain, and matches a resource in this
  document;
- `description` is human-readable text for the subscription UI. It is NOT a stable contract — treat
  it as a label, never parse it;
- Adding an event type is ADDITIVE. Removing one is BREAKING and requires a version bump, because
  subscriptions referencing it would silently stop firing;

### GET /webhooks/{webhook-id}/events
REST request to access an endpoint's subscriptions.

#### Response Body

```json
{
	"data": [
		{
			"id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
			"created_at": "2026-08-12T11:51:00-05:00",
			"webhook_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"event": "transaction.created"
		}
	],
	"meta": {
		"limit": 25,
		"total": 1,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- A subscription is its own resource with its own id, not a string in an array on the endpoint. This
  is what makes unsubscribing a plain DELETE on an addressable URL rather than a whole-array
  replacement that races two concurrent editors;
- An endpoint may hold at most one subscription per event type. The pair is unique;

### POST /webhooks/{webhook-id}/events
REST request to subscribe an endpoint to an event type.

#### Request Body

```json
{
	"event": "transaction.created"
}
```

#### Response Body

Returns the created subscription in the same shape as one element of GET /webhooks/{webhook-id}/events,
with 201.

NOTES:
- `event` must appear in GET /webhooks/event-types. An unknown value fails with 422
  `validation_failed` and detail code `unknown_event_type`;
- Subscribing to an event type the endpoint already has fails with 409 `subscription_exists`. It is a
  conflict rather than a silent success because the user's intent — "add this" — is ambiguous once it
  is already there, and returning 201 for a resource that was not created is a lie;

### DELETE /webhooks/{webhook-id}/events/{subscription-id}
REST request to unsubscribe an endpoint from an event type.

Deletion is permanent. Returns the deleted subscription.

### GET /webhooks/{webhook-id}/deliveries
REST request to access the delivery log for an endpoint.

This is the debugging surface. Without it, "we never received it" is unanswerable — there is no way
to tell a delivery that was never attempted from one that was rejected.

#### Query Params
| param  | values                                                        | default | purpose                    |
|--------|---------------------------------------------------------------|---------|----------------------------|
| limit  | Number                                                        | 25      | Page size, capped at 100   |
| cursor | String                                                        | absent  | Keyset cursor              |
| status | `pending`, `in_progress`, `retry_scheduled`, `success`, `failed` | absent | Restrict to one status  |
| event  | String                                                        | absent  | Restrict to one event type |

#### Response Body

```json
{
	"data": [
		{
			"id": "7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34",
			"created_at": "2026-08-12T11:51:00-05:00",
			"updated_at": "2026-08-12T11:53:30-05:00",
			"webhook_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"event_id": "evt_5f1c8b2a9d",
			"event": "transaction.created",
			"target_url": "https://hooks.example.com/finance/ledger",
			"status": "retry_scheduled",
			"attempts": 2,
			"next_attempt_at": "2026-08-12T11:54:00-05:00",
			"last_error": "sender: non-2xx response: 503"
		},
		{
			"id": "e4a1b7c9-2f80-4d13-a6ce-91b3f0d75a28",
			"created_at": "2026-08-12T10:04:00-05:00",
			"updated_at": "2026-08-12T10:04:01-05:00",
			"webhook_id": "1665b60e-bb7a-4360-8aa6-c1a578d81077",
			"event_id": "evt_2b9d4c7a1e",
			"event": "wallet.updated",
			"target_url": "https://hooks.example.com/finance/ledger",
			"status": "success",
			"attempts": 1,
			"next_attempt_at": null,
			"last_error": null
		}
	],
	"meta": {
		"limit": 25,
		"total": 2,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- The delivery PAYLOAD is not returned. It is stored, but echoing it here doubles the size of every
  log page and can restate money the read model has since superseded. A delivery record answers "was
  it sent and what came back", not "what did it say";
- `attempts` counts attempts MADE, so a `pending` delivery that has never been tried reports `0`;
- `next_attempt_at` is non-`null` only for `pending` and `retry_scheduled`. A finished delivery has
  nothing scheduled;
- `last_error` is a diagnostic string, not a contract. It is safe to display and unsafe to parse;
- `event_id` is stable across every retry of the same event, and is what the receiver deduplicates
  on. It is the value sent in `X-Webhook-Delivery`;
- The log outlives its endpoint. Deleting a webhook does not delete its deliveries;

### Delivery
What the user's server actually receives. This is a contract with THEIR code, so it changes only
under the versioning rules like anything else here.

#### Request

```
POST /finance/ledger HTTP/1.1
Host: hooks.example.com
Content-Type: application/json
X-Webhook-Event: transaction.created
X-Webhook-Delivery: evt_5f1c8b2a9d
X-Webhook-Timestamp: 1786553460
X-Webhook-Signature: v1=8f4c2a...
```

```json
{
	"id": "evt_5f1c8b2a9d",
	"event": "transaction.created",
	"created_at": "2026-08-12T11:51:00-05:00",
	"data": {
		"id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
		"name": "Coffee",
		"money": {
			"amount": "4.20",
			"currency": "USD"
		}
	}
}
```

- The method is always POST and the body is always JSON;
- `data` carries the subject resource in the same shape this API returns it, so a receiver reuses the
  types it already has;
- Money inside `data` follows the Money Shape — decimal strings, never JSON numbers. A receiver
  parsing these into floats has the same rounding problem a client would;

#### Signature
Every request carries `X-Webhook-Signature`:

```
v1=<hex HMAC-SHA256 of "{X-Webhook-Timestamp}.{raw request body}" keyed by the endpoint secret>
```

Rules for verifying, in order:
- Compute over the RAW body bytes, before any JSON parsing. Re-serialising the parsed object changes
  whitespace and key order and produces a different digest;
- Compare in constant time. A byte-by-byte early-exit comparison leaks the expected signature to a
  timing attack;
- REJECT requests whose `X-Webhook-Timestamp` is more than 5 minutes from the receiver's clock.
  Without this check a captured request replays forever, because a valid signature stays valid;
- During a secret rotation grace period a receiver may hold two secrets and accept a match against
  either;

The `v1=` prefix exists so the scheme can change without ambiguity. A receiver must reject a prefix
it does not recognise rather than attempting to verify it.

#### Retries
- Success is any 2xx. Every other status, and every transport failure, is a failure;
- The request times out after 10 seconds. A receiver that needs longer must acknowledge immediately
  and work asynchronously;
- A failed delivery is retried up to 5 attempts total, 30 seconds apart. After the last attempt it
  is marked `failed` and never retried;
- Retries reuse the same `event_id`. A receiver MUST deduplicate on it — at-least-once delivery is
  the guarantee, and a slow receiver that times out after doing the work will see the same event
  again;
- Ordering is NOT guaranteed. A retried event can arrive after a later one succeeded on the first
  attempt. Receivers that care about order must use the payload's `created_at`, not arrival order;

#### Address Restrictions
The target URL is fetched by our infrastructure, so it is constrained to prevent it being used to
reach systems it should not:

- Redirects are NOT followed. A 3xx response is a failed delivery. A redirect chain is a way to pass
  the address guard and then land somewhere else;
- The resolved IP is checked at connection time — after DNS, not before — and connections to
  loopback, private, link-local and unspecified addresses are refused. Checking the hostname instead
  of the resolved address would be defeated by a name that resolves to an internal address only when
  we look it up;
- A URL that passes registration can still fail here, because DNS can change in between. Delivery is
  where the guarantee is enforced;

## Assistant
The conversational surface. Everything else the assistant does — dispatching account postings,
generating actions, enriching transactions — happens at the backend without a request and is
described in those slices. This one is only what the user talks to.

The panel needs three things with three different lifecycles, so they are three different requests:
- SIGNALS and PROMPTS: derived, cheap, cacheable, no user state. Refreshed whenever the panel opens;
- MESSAGES: an append-only conversation that grows without bound and must paginate;
- A REPLY: an expensive, slow, streamed generation;

Bundling them, as a single `content` endpoint would, means every signal refresh re-downloads the
whole conversation and there is nowhere to put a sent message. They are separated for that reason.

There is ONE conversation per user. It is a rolling thread, not a list of sessions — the UI is a
panel with a single feed, and named conversations with their own history is a product decision that
has not been made. Endpoints are shaped so that adding it later means adding a conversation id, not
restructuring the slice.

The assistant never mutates financial data through this slice. When it wants the user to change
something it raises an ACTION, which the user resolves explicitly — see Actions. A chat reply cannot
move money, and there is deliberately no endpoint here that lets it.

### GET /assistant/overview
REST request to access the assistant's headline signals and suggested prompts.

#### Query Params
No query params are supported

#### Response Body

```json
{
	"data": {
		"signals": [
			{
				"label": "Runway",
				"value": "4.2 months",
				"tone": "positive"
			},
			{
				"label": "Dining vs last month",
				"value": "+38%",
				"tone": "negative"
			},
			{
				"label": "Uncategorised",
				"value": "3 transactions",
				"tone": "muted"
			}
		],
		"prompts": [
			"Where did my money go last month?",
			"Can I afford a 1,200.00 USD laptop?",
			"Why is my dining spend up?"
		]
	},
	"meta": {}
}
```
NOTES:
- `signals[].value` is a PREFORMATTED display string, and is the one deliberate exception to the rule
  that this API never formats. A signal is a sentence fragment composed by the assistant — "4.2
  months", "+38%", "3 transactions" — with no fixed unit, no fixed type, and nothing for a client to
  compute from. It is text, and it is rendered verbatim. Nothing here is money in the Money Shape
  sense, and clients must never parse a value back into a number;
- Because the value is generated text, it is in the user's `language` preference. See Conventions →
  User Preferences;
- `prompts` are suggestion chips, not a closed set and not stable between requests. They are input
  to POST /assistant/messages exactly as if the user had typed them;
- Both collections are small, complete and not paginated;
- This endpoint is safe to poll and is cached. It carries `meta.cached` like any read;

### GET /assistant/messages
REST request to access the conversation history.

#### Query Params
| param  | values | default | purpose                  |
|--------|--------|---------|--------------------------|
| limit  | Number | 25      | Page size, capped at 100 |
| cursor | String | absent  | Keyset cursor            |

#### Response Body

```json
{
	"data": [
		{
			"id": "e4a1b7c9-2f80-4d13-a6ce-91b3f0d75a28",
			"created_at": "2026-08-12T11:51:02-05:00",
			"role": "assistant",
			"status": "complete",
			"text": "You spent 412.30 USD on dining last month, up 38% from July. The increase is mostly four weekend restaurant visits.",
			"refs": [
				{
					"type": "transaction",
					"id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92"
				},
				{
					"type": "wallet",
					"id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40"
				}
			]
		},
		{
			"id": "7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34",
			"created_at": "2026-08-12T11:51:00-05:00",
			"role": "user",
			"status": "complete",
			"text": "Why is my dining spend up?",
			"refs": []
		}
	],
	"meta": {
		"limit": 25,
		"total": 2,
		"next_cursor": null,
		"prev_cursor": null
	}
}
```
NOTES:
- Ordering is the global default — `created_at DESC, id DESC`, newest first. A chat feed reads
  oldest-first, so the client REVERSES each page for display. The API does not invert its ordering
  for one endpoint: paging backwards through a conversation means fetching newest-first, and a feed
  that paginated oldest-first would have to know the total length before it could start;
- `refs` is an array of the same polymorphic `{type, id}` references Actions and Notifications use,
  and is what makes a cited figure clickable. It is `[]`, never `null`, and never absent — an
  assistant message that cites nothing has an empty array;
- `refs` are not links in the text. The API does not mark up WHERE a reference occurs in `text`, so a
  client renders them as a list of chips beside the message rather than as inline anchors;
- `status` distinguishes a completed message from one still generating (`streaming`) or abandoned
  (`failed`). A history fetch can legitimately return a `streaming` message if another tab is
  mid-generation;
- User messages always have `status: "complete"` and empty `refs`;

### POST /assistant/messages
REST request to send a message and receive the assistant's reply.

**This endpoint responds with a stream.** It is the second exception to the response envelope in this
document, alongside GET /notifications/stream, and for the same reason: a generated reply arrives
progressively and a client that waits for the whole thing before rendering feels broken. The request
is ordinary JSON; the RESPONSE is `text/event-stream`.

#### Request Body

```json
{
	"text": "Why is my dining spend up?"
}
```

#### Response

```
event: accepted
data: {"user_message_id":"7c3e9a10-4d2b-4f77-91cc-5e8b0a2f6d34","message_id":"e4a1b7c9-2f80-4d13-a6ce-91b3f0d75a28"}

event: delta
data: {"text":"You spent 412.30 USD on dining "}

event: delta
data: {"text":"last month, up 38% from July."}

event: message
data: {"id":"e4a1b7c9-2f80-4d13-a6ce-91b3f0d75a28","created_at":"2026-08-12T11:51:02-05:00","role":"assistant","status":"complete","text":"You spent 412.30 USD on dining last month, up 38% from July.","refs":[{"type":"transaction","id":"b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92"}]}
```

| event      | meaning                                                                  |
|------------|--------------------------------------------------------------------------|
| `accepted` | both messages are persisted; carries their ids before any text exists    |
| `delta`    | an increment of reply text. Concatenate in arrival order                 |
| `message`  | the finished message, complete with `refs`. Replaces the accumulated text |
| `error`    | generation failed. Terminal                                              |

NOTES:
- `accepted` arrives FIRST and before any generation, so a client that disconnects immediately still
  knows both ids. It is what makes recovery possible;
- `delta` carries text only. `refs` are not known until generation completes, which is why the
  terminal `message` event repeats the full text rather than only announcing the end — a client
  renders deltas for responsiveness and then replaces them with the authoritative message;
- The reply is PERSISTED regardless of whether the client is still listening. A dropped connection
  loses the live view, not the answer: refetching GET /assistant/messages returns it. This endpoint
  is not resumable — there is no partial-generation replay — and reconnecting means refetching, not
  re-sending. Re-sending would generate a second reply and bill for it;
- If generation fails the message is stored with `status: "failed"` and whatever text was produced.
  It is not deleted, because a user who watched half an answer appear and then vanish has no way to
  tell that from a bug;
- `Idempotency-Key` is optional but recommended. A double-submitted message otherwise costs a second
  generation and puts two identical questions in the history;
- Rate limits here are STRICTER than the per-user tier in Conventions, because each request is an
  expensive upstream call rather than a database read. Exceeding them is 429 `rate_limited` like
  anywhere else;
- The endpoint fails with 503 `assistant_unavailable` when the upstream model is unreachable. This is
  503 rather than 500 because it is transient and retrying is the correct client response;

### DELETE /assistant/messages
REST request to clear the conversation.

#### Response Body

```json
{
	"data": {
		"deleted": 42
	},
	"meta": {}
}
```
NOTES:
- Deletes the entire conversation for the user. There is no per-message deletion: a conversation with
  holes in it produces worse answers than one that was cleared, because the assistant reads the
  history as context and a half-deleted exchange reads as a non-sequitur;
- This is a HARD delete. The point of the button is that the content is gone;
- It does not affect anything the assistant produced elsewhere. Actions it raised, postings it
  dispatched and enrichment it applied all survive — those are financial records, not conversation;
- `deleted` is a count, and is `0` when the conversation was already empty. Clearing an empty
  conversation succeeds;
