"""Idempotency-Key support for write-side endpoints.

Public surface:

* `@idempotent(required=True|False)` — decorator applied to async view methods.
* `RedisIdempotencyStore` — Redis-backed lock + response cache.
* Exceptions translated to HTTP responses by DRF's exception handler.

Wired against `write-redis` (see compose.yaml). For money-moving endpoints
the decorator is `required=True`; missing Idempotency-Key returns 400 and a
Redis outage returns 503 (fail-closed). For non-money endpoints
`required=False` is used: missing key passes through, Redis outage is
logged and the request proceeds.
"""

from .atomic_redis import RedisIdempotencyStore, StoredResponse
from .decorator import idempotent
from .exceptions import (
    IdempotencyError,
    IdempotencyInFlight,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    IdempotencyUnavailable,
)

__all__ = [
    "IdempotencyError",
    "IdempotencyInFlight",
    "IdempotencyKeyRequired",
    "IdempotencyKeyReused",
    "IdempotencyUnavailable",
    "RedisIdempotencyStore",
    "StoredResponse",
    "idempotent",
]
