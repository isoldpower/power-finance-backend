# Analytics API — v1

Read-only aggregation endpoints behind `services/analytics`. They live next to the finance v1 resources
(same host, same auth, same envelope) under **`/api/v1/analytics/*`** and are computed from the existing
`transactions`, `wallets` and currency-rate data. There are no writes.

The frontend already ships a mock of every endpoint
(`services/analytics/src/features/*/*-api/rest-client/mock-server.ts`) and contract tests for its shapes.
The backend must return the same shapes; when this document is ambiguous, the mock is the reference.
Switching the client to the real API is `CLIENT_API_MODE=live` in `services/analytics/.env`.

---

## 1. Requirements at a glance

1. 11 `GET` endpoints, listed in §3. All responses use the finance envelope `{ "data", "meta" }`.
2. Same auth and headers as finance. Honour `Read-At-Least` and return `507` when the data is staler than requested.
3. Convert every amount into the requested `currency`, using the rate for the transaction's day.
4. Exclude **transfers** (`chain_id IS NOT NULL`) from every income or expense figure, but **include** them in balances.
5. Time series are **zero-filled and continuous**: every bucket, day or hour cell is present, even when empty.
6. Cut days, weeks (ISO, Monday start), months and hours in the requested `timezone`.
7. Ordering and the fold of extra series into "other" are part of the contract. The charts rely on them.
8. Reject bad input with `validation_failed` and the detail codes in §2.7. Never return a partial result silently.

---

## 2. Conventions

### 2.1 Transport

| Topic | Rule |
| --- | --- |
| Base path | `/api/v1/analytics` |
| Auth | `Authorization: Bearer <clerk session token>`, identical to finance. `X-Demo-Session`, `X-Sandbox` and `X-Correlation-Id` are honoured exactly as on finance resources. |
| Consistency | After a finance write, the shared transport sends `Read-At-Least: <write version>`. Never answer from data older than that version. If you cannot catch up, reply with status `507`, as other finance reads do. |
| Success | `{ "data": …, "meta": … }` |
| Error | `{ "error": { "code", "message", "details": [{ "field", "code", "message" }] }, "meta": { "request_id", "timestamp" } }` |
| Money | `MoneyDto = { "amount": "<decimal string>", "currency": "<ISO 4217>" }`. Amounts are positive magnitudes unless the field is explicitly signed (`net`, balances). Round to the currency's minor unit. |
| Timestamps | ISO 8601 with offset (`2026-11-12T08:30:00Z`). Calendar dates are `YYYY-MM-DD`. |
| Keys | snake_case |
| Arrays in the query | **Comma-joined**: `wallet_id=w_1,w_2`, `category=Rent,__none__`. The client never sends repeated keys or `[]` suffixes. Empty arrays are omitted. |

### 2.2 Shared query parameters

Every endpoint except `/dimensions` accepts:

| Param | Type | Default | Meaning |
| --- | --- | --- | --- |
| `since` | ISO datetime | `until − 30 days` | Inclusive start of the window |
| `until` | ISO datetime | now | **Exclusive** end. `until ≤ since` → `range_invalid`. Longer than 5 years → `range_too_long`. |
| `currency` | ISO 4217 | user's main currency (Clerk preferences), else `USD` | Target currency for every `MoneyDto`. Unsupported → `unsupported_currency` (422). |
| `wallet_id` | comma list | all non-deleted wallets | Restricts the ledger to these wallets. Unknown or foreign id → `wallet_unknown`. |
| `timezone` | IANA zone | `UTC` | Zone used for day, week and month boundaries and for hour of day |
| `category` | comma list | none | Only on endpoints marked *category filter*. `__none__` selects uncategorised rows. |

The client always sends `since`, `until`, `currency` and `timezone`. It sends `wallet_id` only when the
user narrows wallets.

### 2.3 Reserved tokens

| Token | Meaning |
| --- | --- |
| `__none__` | Uncategorised (`category IS NULL`). Used in the `category` filter, in series `key`s and inside node ids. |
| `__other__` | Roll-up of the categories beyond `limit` in `/category-trends` |

A category name containing a comma cannot be expressed in the `category` filter. Either reject commas in
category names or document an escape before the client relies on it.

### 2.4 Ledger semantics (apply everywhere)

- Only non-deleted rows count (`deleted_at IS NULL`).
- **Transfers** are rows with a non-null `chain_id`. They are excluded from inflow, outflow, net, categories,
  counterparties, calendar, rhythm and money flow. They are **included** in `closing_balance` and
  `/balance-history`.
- `inflow` = Σ `type = income`, `outflow` = Σ `type = expense`, `net` = `inflow − outflow` (signed).
- `savings_rate` = `net / inflow × 100`, 2 decimals, `null` when `inflow = 0`.
- Wallet balance at instant *t* = `opening_balance` + Σ signed deltas of the rows with `created_at ≤ t`
  (income +, expense −, transfer legs ± per leg).
- `share` = percentage (0–100, 2 decimals) of that endpoint's own total.
- `change_percentage` = `(current − previous) / previous × 100`, 2 decimals, `null` when `previous = 0`.
- The **previous window** of `[since, until)` is `[since − (until − since), since)`.
- **Conversion** uses the rate of the transaction's day, falling back to the latest known rate. Use the same
  source as `/currencies/rates`. If no rate exists at all, return `rate_unavailable`.

### 2.5 Shared meta

```jsonc
"meta": {
  "since": "2026-10-13T00:00:00Z",   // effective window after defaults
  "until": "2026-11-12T00:00:00Z",
  "currency": "USD",
  "timezone": "Europe/Berlin",
  "wallet_ids": null,                // null = all wallets, else the effective list
  "categories": null,                // null = no category filter, else the effective list
  "generated_at": "2026-11-12T08:30:01Z",
  "cached": false                    // optional, true when served from an aggregate cache
}
```

Endpoint-specific meta fields are merged into this object.

### 2.6 Shared shapes

```ts
type LedgerSide = 'expense' | 'income';
type Granularity = 'day' | 'week' | 'month';

interface WalletRefDto    { id: string; name: string; color: string }        // color = wallet.color (hex)
interface WalletOptionDto extends WalletRefDto { currency: string }         // wallet's own currency

interface TransactionBriefDto {
  id: string;
  name: string;
  created_at: string;
  type: LedgerSide;
  category: string | null;
  wallet: WalletRefDto;
  money: MoneyDto;       // native amount, wallet currency
  converted: MoneyDto;   // same amount in the requested currency
}
```

### 2.7 Granularity

Endpoints with a time axis accept `granularity`. If it is omitted, choose it from the window length:

| Window | Granularity |
| --- | --- |
| ≤ 45 days | `day` |
| ≤ 200 days | `week` |
| longer | `month` |

- More than 400 buckets → `granularity_too_fine`.
- Align buckets to calendar boundaries in `timezone`, with weeks starting on Monday.
- Clip the first and last bucket to the window.
- Always include empty buckets, zero-filled.
- Echo the effective value as `meta.granularity`.

### 2.8 Validation detail codes

All of these use `error.code = validation_failed` (422), with one `details[]` entry naming the offending `field`:

| Detail code | When |
| --- | --- |
| `range_invalid` | `until ≤ since`, or an unparsable datetime |
| `range_too_long` | Window longer than 5 years, or longer than 366 days on `/spending-calendar` |
| `granularity_too_fine` | More than 400 buckets |
| `wallet_unknown` | `wallet_id` not owned by the user |
| `limit_out_of_range` | `limit` outside the endpoint's bounds |
| `points_out_of_range` | `points` outside 2–120 |
| `type_invalid` | `type` not `expense` or `income` |
| `order_invalid` | Unknown `order` |

`unsupported_currency` (422) and `rate_unavailable` (409) are top-level error codes, as on finance.

---

## 3. Endpoints

| # | Endpoint | Extra params | Category filter | Used by |
| --- | --- | --- | --- | --- |
| 3.1 | `GET /dimensions` | — | — | wallet filter, page header |
| 3.2 | `GET /overview` | — | — | Overview: KPI strip, insights |
| 3.3 | `GET /cash-flow` | `granularity` | ✓ | Overview: cash flow, pace (×2, current and previous window). Flow: surplus |
| 3.4 | `GET /categories` | `type` | ✓ | Overview and Spending: breakdown donut, radar, radial and list |
| 3.5 | `GET /category-trends` | `type`, `granularity`, `limit` | ✓ | Spending: categories over time |
| 3.6 | `GET /money-flow` | — | — | Flow: Sankey |
| 3.7 | `GET /spending-calendar` | — | — | Spending: calendar heatmap |
| 3.8 | `GET /spending-rhythm` | `type` | — | Spending: weekday × hour heatmap |
| 3.9 | `GET /balance-history` | `points` | — | Flow: balance history and brush |
| 3.10 | `GET /counterparties` | `type`, `limit` | ✓ | Spending: top merchants / payers |
| 3.11 | `GET /transactions` | `type`, `name`, `order`, `limit` | ✓ | Drill-down panel on every chart |

### 3.1 `GET /analytics/dimensions`

The filter vocabulary. It ignores the range params and accepts `currency` only to echo it back.

```jsonc
{
  "data": {
    "wallets": [WalletOptionDto],                     // non-deleted, favorite DESC, name ASC
    "categories": {
      "expense": ["Dining", "Groceries", "Rent"],     // distinct non-null names, A→Z
      "income": ["Freelance", "Salary"]
    },
    "first_transaction_at": "2025-09-02T09:12:00Z",   // null when the ledger is empty
    "last_transaction_at": "2026-11-11T19:40:00Z"
  },
  "meta": { "currency": "USD", "generated_at": "…" }
}
```

### 3.2 `GET /analytics/overview`

Headline totals for the window and for the previous window.

```jsonc
{
  "data": { "current": PeriodSummaryDto, "previous": PeriodSummaryDto },
  "meta": { …shared }
}

PeriodSummaryDto = {
  "since": "…", "until": "…",
  "inflow": MoneyDto, "outflow": MoneyDto, "net": MoneyDto,
  "savings_rate": 23.4 | null,
  "transactions_count": 182,                 // income + expense rows (no transfers)
  "active_days": 27,                         // days (in timezone) with ≥ 1 income/expense row
  "average_daily_outflow": MoneyDto,         // outflow / number of days in the window
  "largest_expense": TransactionBriefDto | null,
  "largest_income": TransactionBriefDto | null,
  "top_expense_category": { "category": "Rent" | null, "amount": MoneyDto, "share": 38.2 } | null
}
```

### 3.3 `GET /analytics/cash-flow`

Inflow and outflow per time bucket.

| Param | Values |
| --- | --- |
| `granularity` | `day` \| `week` \| `month`, optional (§2.7) |
| `category` | category filter |

```jsonc
{
  "data": {
    "buckets": [{
      "start": "2026-10-13T00:00:00Z", "end": "2026-10-14T00:00:00Z",
      "inflow": MoneyDto, "outflow": MoneyDto, "net": MoneyDto,
      "transactions_count": 6,
      "closing_balance": MoneyDto            // signed balance of the selected wallets at `end`, transfers included
    }],                                      // chronological, zero-filled
    "totals": { "inflow": MoneyDto, "outflow": MoneyDto, "net": MoneyDto }
  },
  "meta": { …shared, "granularity": "day" }
}
```

For the spending-pace chart, the client calls this twice with the same granularity: once for the window
and once for the previous window.

### 3.4 `GET /analytics/categories`

One side of the ledger broken down by category.

| Param | Values |
| --- | --- |
| `type` | `expense` (default) \| `income` |
| `category` | category filter |

```jsonc
{
  "data": {
    "type": "expense",
    "total": MoneyDto,
    "categories": [{
      "category": "Rent" | null,
      "amount": MoneyDto,
      "share": 38.21,
      "transactions_count": 1,
      "average": MoneyDto,                   // amount / transactions_count
      "previous_amount": MoneyDto,           // same category, previous window (zero if absent)
      "change_percentage": 4.1 | null
    }]                                       // amount DESC; omit categories with no rows in the window
  },
  "meta": { …shared }
}
```

Return **all** categories. When there are more than 7, the client shows the top 6 and folds the rest into its own "Other" slice.

### 3.5 `GET /analytics/category-trends`

Per-category series in columns, for the stacked area chart and the streamgraph.

| Param | Values |
| --- | --- |
| `type` | `expense` (default) \| `income` |
| `granularity` | optional (§2.7) |
| `limit` | 1–7, default 6. The client sends 6. |
| `category` | category filter. When given, ignore `limit`, return exactly those categories and no `other` series. |

```jsonc
{
  "data": {
    "type": "expense",
    "buckets": [{ "start": "…", "end": "…" }],   // chronological, zero-filled, same as /cash-flow
    "series": [{
      "key": "Rent",                             // category name | "__none__" | "__other__"
      "category": "Rent" | null,                 // null for uncategorised AND for the other roll-up
      "kind": "category" | "other",
      "total": MoneyDto,
      "points": [MoneyDto]                       // exactly one per bucket, same order as `buckets`
    }]                                           // top `limit` by total DESC, then one "other" if anything remains
  },
  "meta": { …shared, "granularity": "week" }
}
```

### 3.6 `GET /analytics/money-flow`

A three-column, acyclic flow: income categories → wallets → expense categories.

```jsonc
{
  "data": {
    "nodes": [{
      "id": "income:Salary",       // "income:<category|__none__>" | "wallet:<id>" | "expense:<category|__none__>" | "savings" | "reserves"
      "kind": "income_category" | "wallet" | "expense_category" | "savings" | "reserves",
      "label": "Salary",           // wallet name for wallets, "Saved" for savings, "From balance" for reserves
      "category": "Salary" | null,
      "wallet": WalletRefDto | null,   // set only when kind = wallet
      "amount": MoneyDto               // max(total in, total out) of the node
    }],
    "links": [{ "source": "income:Salary", "target": "wallet:w_1", "amount": MoneyDto }],
    "totals": { "inflow": MoneyDto, "outflow": MoneyDto }
  },
  "meta": { …shared }
}
```

Rules:

- `income:<c> → wallet:<w>`: income of category *c* booked on wallet *w*.
- `wallet:<w> → expense:<c>`: expenses of category *c* paid from wallet *w*.
- When a wallet's income exceeds its expenses, the surplus flows `wallet:<w> → savings`.
- When a wallet's expenses exceed its income, the gap flows `reserves → wallet:<w>`.
- Each `(source, target)` pair appears **at most once**. The client uses the pair as the link identity when it animates between filters.
- Omit links with a zero amount and nodes with no links. Transfers are excluded, so the graph is always acyclic.

### 3.7 `GET /analytics/spending-calendar`

One entry per calendar day in `timezone`, for the heatmap calendar. The window is capped at 366 days
(`range_too_long`).

```jsonc
{
  "data": {
    "days": [{
      "date": "2026-10-13",
      "inflow": MoneyDto, "outflow": MoneyDto, "net": MoneyDto,
      "transactions_count": 4
    }],                                          // every day of the window, chronological, zero-filled
    "peak_outflow": MoneyDto                     // max single-day outflow; zero when empty
  },
  "meta": { …shared }
}
```

### 3.8 `GET /analytics/spending-rhythm`

Weekday × hour-of-day matrix in `timezone`.

| Param | Values |
| --- | --- |
| `type` | `expense` (default) \| `income` |

```jsonc
{
  "data": {
    "type": "expense",
    "cells": [{ "weekday": 1, "hour": 0, "amount": MoneyDto, "transactions_count": 0 }],
    "peak": { "weekday": 5, "hour": 19, "amount": MoneyDto } | null   // null when every cell is zero
  },
  "meta": { …shared }
}
```

`cells` always has all 168 entries, ordered by weekday then hour. `weekday` is ISO (1 = Monday … 7 = Sunday)
and `hour` runs 0–23.

### 3.9 `GET /analytics/balance-history`

Evenly spaced balance samples, per wallet and in total.

| Param | Values |
| --- | --- |
| `points` | 2–120, default 40. The client sends 90. |

```jsonc
{
  "data": {
    "timestamps": ["…"],               // `points` instants, evenly spaced, first = since, last = until
    "total": [MoneyDto],               // Σ converted wallet balances per timestamp (signed)
    "wallets": [{
      "wallet": WalletOptionDto,
      "balances": [MoneyDto],          // converted into `currency`, signed, one per timestamp
      "native_balances": [MoneyDto]    // in the wallet's own currency, signed
    }]                                 // same order as /dimensions
  },
  "meta": { …shared, "points": 90 }
}
```

Balances include transfers and are measured from the wallet's `opening_balance`, not from zero at `since`.

### 3.10 `GET /analytics/counterparties`

Who the money goes to or comes from. Rows are grouped by transaction `name`, trimmed and compared
case-insensitively; return the most frequent original spelling.

| Param | Values |
| --- | --- |
| `type` | `expense` (default) \| `income` |
| `limit` | 1–25, default 10. The client sends 8. |
| `category` | category filter |

```jsonc
{
  "data": [{
    "name": "Corner Market",
    "category": "Groceries" | null,    // the counterparty's most frequent category
    "amount": MoneyDto,
    "share": 12.5,                     // of the side's total in the window
    "transactions_count": 9,
    "average": MoneyDto,
    "last_seen_at": "…"
  }],                                  // amount DESC, at most `limit`
  "meta": { …shared, "total_counterparties": 41 }   // distinct counterparties before `limit`
}
```

### 3.11 `GET /analytics/transactions`

The drill-down list behind any chart element: a day, a bucket, a category, a wallet or a counterparty. The
client narrows it with the shared params (window, `wallet_id`) plus the filters below.

| Param | Values |
| --- | --- |
| `type` | optional. Both sides when omitted. |
| `category` | category filter (`__none__` allowed) |
| `name` | exact counterparty match, normalised as in §3.10 |
| `order` | `amount_desc` (default) \| `created_desc` |
| `limit` | 1–50, default 20. The client sends 50. |

```jsonc
{
  "data": [TransactionBriefDto],       // at most `limit`, in `order`
  "meta": {
    …shared,
    "total": 37,                       // all matching rows, ignoring `limit`
    "total_inflow": MoneyDto,          // over all matching rows
    "total_outflow": MoneyDto
  }
}
```

This endpoint is not paginated. The panel shows the top `limit` rows plus the totals.

---

## 4. Implementation notes

- Every endpoint can be derived from one query over `transactions` joined to `wallets` for the window. Overview
  and categories also need the previous window, and balances need history up to `until`. Aggregating in
  Python after that fetch is fine at current volumes.
- Cache per `(user, endpoint, normalised params, latest write version)` and set `meta.cached`. Invalidation then
  follows from the write version, which also satisfies `Read-At-Least`.
- Respect sandbox and demo sessions: the same headers select the same isolated ledger as on finance.
- Shapes, ordering, zero-filling and the "other" fold are contract. Changing any of them breaks the charts.

## 5. Acceptance checklist

- [ ] All 11 endpoints respond with the shapes above for a ledger containing income, expenses, transfers,
      uncategorised rows and at least two wallet currencies.
- [ ] A transfer changes `/balance-history` and `closing_balance` but no inflow, outflow, category, calendar,
      rhythm, counterparty or money-flow figure.
- [ ] `/cash-flow` and `/category-trends` return identical `buckets` for the same window and granularity.
- [ ] Empty days, buckets and rhythm cells are present with zero amounts.
- [ ] `wallet_id=a,b`, `category=Rent,__none__` and `timezone=America/New_York` behave as specified.
- [ ] Each validation code in §2.8 is reachable and names the right `field`.
- [ ] With `CLIENT_API_MODE=live`, the Overview, Spending and Flow pages render with no console errors.
