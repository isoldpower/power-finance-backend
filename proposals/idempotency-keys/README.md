# Idempotency Keys

## Why

Financial APIs are called over unreliable networks. A client sends `POST /transactions`, the server processes it, then the response is lost. The client retries. Without idempotency, the transaction is created twice. This is unacceptable in any financial system.

Idempotency keys let clients safely retry any mutating request — the server returns the same result for the same key without re-executing the operation.

## Production Concepts Taught

- Idempotency as a first-class API contract
- Request deduplication using Redis
- Storing and replaying responses
- Concurrency safety — two simultaneous requests with same key
- TTL-based key expiration strategy
- Client-side key generation patterns

## How It Works

1. Client generates UUID key: `Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000`
2. Client sends request with key in header
3. Server checks Redis: key seen before?
   - **No** → process request, store `(key → serialized response)` in Redis, return response
   - **Yes, complete** → return stored response, skip processing
   - **Yes, in-flight** → return `409 Conflict` (another request with same key is processing)
4. Key expires after 24h (configurable)

## Endpoints to Apply

All state-mutating financial endpoints:

- `POST /wallets/`
- `POST /transactions/`
- `PUT /transactions/{id}/`
- `DELETE /transactions/{id}/`
- `POST /transfers/` (when money transfers implemented)
- `POST /subscriptions/` (when subscriptions implemented)

## Redis Key Schema

```
idempotency:{user_id}:{idempotency_key} → {
  "status": "complete" | "in_flight",
  "response_status": 201,
  "response_body": {...},
  "created_at": "2024-01-01T00:00:00Z"
}
```

TTL: 86400s (24 hours)

## Request Flow

```
Request arrives
    │
    ▼
Extract Idempotency-Key header
    │
    ├── Missing header → 400 Bad Request
    │
    ▼
Redis GET idempotency:{user}:{key}
    │
    ├── EXISTS + status=complete  → return cached response (200/201/etc.)
    ├── EXISTS + status=in_flight → return 409 Conflict
    │
    ▼
Redis SET idempotency:{user}:{key} {status: in_flight} NX EX 86400
    │
    ├── SET failed (NX race) → another request won → 409 Conflict
    │
    ▼
Execute use case
    │
    ├── Success → update Redis {status: complete, response: ...} → return response
    └── Error   → delete Redis key (allow retry) → return error
```

## Implementation Notes

- Use **Redis NX** (set if not exists) for atomic in-flight locking — prevents race condition where two simultaneous retries both pass the "not seen" check
- Scope keys to `user_id` — different users can reuse same UUID
- Only cache **successful responses** (2xx). Errors delete the key so client can retry after fixing the error
- Middleware or DRF mixin both work — middleware cleaner for applying broadly
- Store full HTTP response (status code + body) so replay is byte-identical

## Key Blockwalls

- Race condition: two simultaneous requests with same key both see "not found"
- Error handling: should a 400 (client error) be cached? (No — client should fix and retry)
- Partial failure: request processed in DB but Redis write failed — key never stored, next retry re-executes
- Large response bodies in Redis — consider size limits

## API Contract for Clients

```
Header: Idempotency-Key: <uuid-v4>

Responses:
  200/201  — original response (or replayed)
  400      — missing or malformed key
  409      — same key currently in flight
```
