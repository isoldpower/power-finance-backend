"""Redis-backed idempotency store.

A single key holds either an in-flight marker (short TTL) or a stored
response (long TTL). State transitions:

    (absent) --acquire--> in_flight --store_response--> completed
                              \\
                               --release_lock--> (absent)   # on handler error

`try_acquire` is implemented as a Lua script so the "check + set if free"
is atomic against concurrent attempts on the same key.

The store is decoupled from Django: a `RedisIdempotencyStore` instance is
built from settings at process start and injected into the decorator. That
keeps the decorator unit-testable with an in-memory fake.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from redis.asyncio import Redis
from redis.exceptions import RedisError

_LOCK_VALUE = "__lock__"


@dataclass(frozen=True, slots=True)
class StoredResponse:
    status_code: int
    body: Any
    headers: dict[str, str]
    request_hash: str


@dataclass(frozen=True, slots=True)
class Acquired:
    kind: Literal["acquired"] = "acquired"


@dataclass(frozen=True, slots=True)
class AlreadyCompleted:
    response: StoredResponse
    kind: Literal["completed"] = "completed"


@dataclass(frozen=True, slots=True)
class InProgress:
    kind: Literal["in_progress"] = "in_progress"


@dataclass(frozen=True, slots=True)
class Mismatch:
    stored_hash: str
    kind: Literal["mismatch"] = "mismatch"


AcquireResult = Acquired | AlreadyCompleted | InProgress | Mismatch


# KEYS[1] = idempotency key, ARGV[1] = lock payload JSON, ARGV[2] = lock TTL seconds
_ACQUIRE_SCRIPT = """
local existing = redis.call('GET', KEYS[1])
if existing == false then
    redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
    return {'acquired'}
end
return {'existing', existing}
"""


class StoreUnavailable(RuntimeError):
    """Raised when Redis is unreachable; the caller decides fail-open vs fail-closed."""


class RedisIdempotencyStore:
    def __init__(
        self,
        redis: Redis,
        *,
        key_prefix: str = "idem:",
        lock_ttl_seconds: int = 30,
        response_ttl_seconds: int = 86_400,
    ) -> None:
        self._redis = redis
        self._prefix = key_prefix
        self._lock_ttl = lock_ttl_seconds
        self._response_ttl = response_ttl_seconds
        self._acquire = self._redis.register_script(_ACQUIRE_SCRIPT)

    def _key(self, user_id: int | str, idempotency_key: str) -> str:
        return f"{self._prefix}{user_id}:{idempotency_key}"

    async def try_acquire(
        self, user_id: int | str, idempotency_key: str, request_hash: str
    ) -> AcquireResult:
        redis_key = self._key(user_id, idempotency_key)
        lock_payload = json.dumps(
            {"state": "in_flight", "request_hash": request_hash},
            separators=(",", ":"),
        )
        try:
            result = await self._acquire(
                keys=[redis_key],
                args=[lock_payload, self._lock_ttl],
            )
        except RedisError as exc:
            raise StoreUnavailable(str(exc)) from exc

        if result[0] == b"acquired" or result[0] == "acquired":
            return Acquired()

        # Slot already occupied — decode the existing entry.
        raw = result[1]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            existing = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return InProgress()  # corrupt — treat conservatively

        stored_hash = existing.get("request_hash", "")
        if stored_hash and stored_hash != request_hash:
            return Mismatch(stored_hash=stored_hash)

        if existing.get("state") == "completed":
            return AlreadyCompleted(
                response=StoredResponse(
                    status_code=int(existing["status_code"]),
                    body=existing.get("body"),
                    headers=existing.get("headers", {}),
                    request_hash=stored_hash,
                )
            )
        return InProgress()

    async def store_response(
        self,
        user_id: int | str,
        idempotency_key: str,
        *,
        request_hash: str,
        status_code: int,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(
            {
                "state": "completed",
                "request_hash": request_hash,
                "status_code": status_code,
                "body": body,
                "headers": headers or {},
            },
            separators=(",", ":"),
            default=str,
        )
        try:
            await self._redis.set(
                self._key(user_id, idempotency_key),
                payload,
                ex=self._response_ttl,
            )
        except RedisError as exc:
            raise StoreUnavailable(str(exc)) from exc

    async def release_lock(self, user_id: int | str, idempotency_key: str) -> None:
        """Remove the in-flight marker so the client can retry.

        Best-effort — a Redis failure here is logged at the caller, never
        propagated, because the request has already failed for other reasons.
        """
        with contextlib.suppress(RedisError):
            await self._redis.delete(self._key(user_id, idempotency_key))


__all__ = [
    "Acquired",
    "AcquireResult",
    "AlreadyCompleted",
    "InProgress",
    "Mismatch",
    "RedisIdempotencyStore",
    "StoreUnavailable",
    "StoredResponse",
    "_LOCK_VALUE",
]
