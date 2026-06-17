"""Idempotency-Key support for write-side endpoints: the `@idempotent` decorator
plus a Redis-backed lock + response cache, wired against `write-redis`."""

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
