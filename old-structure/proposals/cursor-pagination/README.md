# Cursor-Based Pagination

## Why

Offset pagination (`LIMIT 100 OFFSET 10000`) requires the database to scan and discard 10,000 rows. At scale this is slow, and it produces inconsistent results when new records are inserted mid-session. Cursor pagination uses a stable position marker — it's O(1) regardless of how deep into the result set you are.

## Production Concepts Taught

- Keyset / cursor pagination vs. offset pagination
- Opaque cursor encoding (base64 encoded position)
- Stable sort requirements for correct pagination
- Handling cursor invalidation (deleted records)
- Bidirectional pagination (next/previous)
- Index design for paginated queries

## The Problem with Offset

```sql
-- Page 100 of transactions, 20 per page:
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 20 OFFSET 1980;
-- DB must scan 2000 rows and discard 1980.

-- If a new transaction is inserted between page 1 and page 2:
-- Page 1: rows 1-20 (correct)
-- Page 2: row 20 repeated (the insert pushed everything down)
```

## Cursor Pagination

```sql
-- First page:
SELECT * FROM transactions
WHERE user_id = $1
ORDER BY created_at DESC, id DESC
LIMIT 21;  -- fetch N+1 to detect if next page exists

-- Next page (cursor = last item's (created_at, id)):
SELECT * FROM transactions
WHERE user_id = $1
  AND (created_at, id) < ($cursor_created_at, $cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 21;
```

No scanning. No offset. Consistent under concurrent inserts.

## Cursor Encoding

Cursor is opaque to the client — base64 encoded JSON:

```python
import base64
import json

def encode_cursor(created_at: datetime, id: UUID) -> str:
    payload = {
        "created_at": created_at.isoformat(),
        "id": str(id)
    }
    return base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()

def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = json.loads(base64.urlsafe_b64decode(cursor))
    return datetime.fromisoformat(payload["created_at"]), UUID(payload["id"])
```

Client sees: `"next": "eyJjcmVhdGVkX2F0IjogIjIwMjQtMDEtMDFUMDA6MDA6MDBaIiwgImlkIjogIjU1MGU4NDAwIn0="`
Client does not know or care what's inside.

## Response Shape

```json
{
  "results": [...],
  "pagination": {
    "next": "eyJjcmVh...",
    "previous": "eyJpZCI6...",
    "has_next": true,
    "has_previous": false,
    "page_size": 20
  }
}
```

If `next` is `null`, no more pages.

## Apply To

- `GET /transactions/` — primary candidate, can grow to millions of rows
- `GET /wallets/{id}/transactions/` — same
- `GET /notifications/` — append-only, cursor ideal
- `GET /subscriptions/{id}/history/` — billing history
- `GET /transfers/` — transfer history

## Index Requirements

Cursor queries require a composite index on the sort columns:

```sql
-- For transactions ordered by (created_at DESC, id DESC):
CREATE INDEX CONCURRENTLY idx_transactions_cursor
ON transactions (user_id, created_at DESC, id DESC);
```

Without this index, cursor pagination is slower than offset pagination.

## Edge Cases

| Case | Handling |
|---|---|
| Cursor points to deleted record | Cursor still works — query finds first record *before* that position |
| Empty result | `next: null`, `results: []` |
| `page_size` too large | Cap at max (e.g., 100) |
| Tampered cursor | Catch decode error, return 400 |
| First page | No cursor in request, `previous: null` in response |

## DRF Integration

```python
class CursorPagination(BasePagination):
    page_size = 20
    max_page_size = 100
    ordering = ('-created_at', '-id')  # must be unique + stable

    def paginate_queryset(self, queryset, request, view=None):
        cursor = request.query_params.get('cursor')
        if cursor:
            created_at, id = decode_cursor(cursor)
            queryset = queryset.filter(
                Q(created_at__lt=created_at) |
                Q(created_at=created_at, id__lt=id)
            )
        self._result = list(queryset.order_by(*self.ordering)[:self.page_size + 1])
        self._has_next = len(self._result) > self.page_size
        return self._result[:self.page_size]
```

## Key Blockwalls

- Sort must be **unique** — `created_at` alone is not unique (two records same timestamp); always include `id` as tiebreaker
- Changing sort order invalidates all cursors — treat cursor format as a versioned API
- Bidirectional pagination requires reverse-direction cursor encoding
- `CONCURRENTLY` index creation on large existing table — non-blocking but takes time
