import contextlib
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..exceptions import StoreUnavailable
from .entry_classifier import EntryClassifier
from .entry_codec import EntryCodec
from .outcomes import Acquired, AcquireResult


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
        self._key_prefix = key_prefix
        self._lock_ttl_seconds = lock_ttl_seconds
        self._response_ttl_seconds = response_ttl_seconds

    async def try_acquire(
        self,
        user_id: int | str,
        idempotency_key: str,
        request_hash: str,
    ) -> AcquireResult:
        redis_key = self._compose_redis_key(user_id, idempotency_key)
        lock_payload = EntryCodec.encode_lock_entry(request_hash)

        if await self._claim_slot(redis_key, lock_payload):
            return Acquired()

        existing_entry = await self._fetch_entry(redis_key)
        return EntryClassifier.classify(existing_entry, request_hash)

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
        completed_payload = EntryCodec.encode_completed_entry(
            request_hash=request_hash,
            status_code=status_code,
            body=body,
            headers=headers or {},
        )
        await self._overwrite_with_ttl(
            self._compose_redis_key(user_id, idempotency_key),
            completed_payload,
            ttl_seconds=self._response_ttl_seconds,
        )

    async def release_lock(self, user_id: int | str, idempotency_key: str) -> None:
        with contextlib.suppress(RedisError):
            await self._redis.delete(self._compose_redis_key(user_id, idempotency_key))

    def _compose_redis_key(self, user_id: int | str, idempotency_key: str) -> str:
        return f"{self._key_prefix}{user_id}:{idempotency_key}"

    async def _claim_slot(self, redis_key: str, lock_payload: str) -> bool:
        try:
            was_set = await self._redis.set(
                redis_key,
                lock_payload,
                nx=True,
                ex=self._lock_ttl_seconds,
            )
        except RedisError as exc:
            raise StoreUnavailable(str(exc)) from exc
        return bool(was_set)

    async def _fetch_entry(self, redis_key: str) -> dict[str, Any] | None:
        try:
            raw_entry = await self._redis.get(redis_key)
        except RedisError as exc:
            raise StoreUnavailable(str(exc)) from exc
        return EntryCodec.decode_entry(raw_entry)

    async def _overwrite_with_ttl(self, redis_key: str, payload: str, *, ttl_seconds: int) -> None:
        try:
            await self._redis.set(redis_key, payload, ex=ttl_seconds)
        except RedisError as exc:
            raise StoreUnavailable(str(exc)) from exc


__all__ = ["RedisIdempotencyStore"]
