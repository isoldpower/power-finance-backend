# Rate Limiting & Throttling

## Why

Unprotected APIs get abused — scrapers, credential stuffing, runaway clients, accidental tight loops. Rate limiting protects the service, enforces fair usage, and is a standard production requirement. Redis is already in the stack, making this straightforward to implement well.

## Production Concepts Taught

- Token bucket vs. sliding window algorithms
- Per-user vs. per-IP vs. per-endpoint limits
- Returning `429 Too Many Requests` with `Retry-After`
- Redis atomic operations (INCR + EXPIRE, or sorted sets for sliding window)
- Graduated limits (anonymous < authenticated < premium)
- Distinguishing throttling (slow down) from blocking (hard stop)

## Limit Tiers

| Tier | Who | Limit |
|---|---|---|
| Anonymous | No auth token | 20 req/min |
| Authenticated | Valid Clerk JWT | 200 req/min |
| Write endpoints | POST/PUT/DELETE | 60 req/min per user |
| Analytics | GET /analytics/** | 30 req/min per user |
| Webhook registration | POST /webhooks/ | 10 req/hour per user |

## Algorithms

### Fixed Window (simple, implement first)

```
key = rate_limit:{user_id}:{endpoint_group}:{window_start_minute}
count = INCR key
if count == 1: EXPIRE key 60
if count > limit: reject
```

Weakness: burst at window boundary (100 req at 0:59 + 100 req at 1:00 = 200 req in 2 seconds).

### Sliding Window Log (accurate, implement second)

```
key = rate_limit:{user_id}:{endpoint_group}
now = current timestamp (ms)
window_start = now - 60000

MULTI
  ZREMRANGEBYSCORE key 0 window_start   # remove old entries
  ZADD key now now                       # add current request
  ZCARD key                              # count requests in window
  EXPIRE key 60
EXEC

if count > limit: reject
```

More accurate, slightly more memory.

## Response Headers

Always include rate limit state in response headers:

```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 147
X-RateLimit-Reset: 1704067260
Retry-After: 42          # only on 429
```

## 429 Response Body

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Retry after 42 seconds.",
  "retry_after": 42
}
```

## Implementation Approach

DRF has built-in throttling (`AnonRateThrottle`, `UserRateThrottle`) backed by cache. Override with Redis-backed implementation for:
- Sorted set sliding window (more accurate than DRF's fixed window)
- Custom response headers
- Per-endpoint-group limits (not just global)

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'finances.throttling.UserSlidingWindowThrottle',
        'finances.throttling.AnonThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '200/min',
        'anon': '20/min',
        'writes': '60/min',
        'analytics': '30/min',
    }
}
```

## Key Blockwalls

- Atomic Redis operations — INCR + EXPIRE must be atomic (use Lua script or pipeline)
- Distributed rate limiting — if multiple Gunicorn workers, local memory counters diverge; Redis required
- Clock skew — sliding window requires consistent timestamps across processes
- Bypass via IP rotation — rate limit by user_id for authenticated endpoints, not IP

## Celery Webhook Delivery

Apply rate limiting to outbound webhook delivery too — don't hammer a failing endpoint. This extends existing retry logic with backoff awareness.
