"""RedisIdempotencyStore: NX-set lock with TTL, fetch-and-classify and completed-
response overwrite, exercised against a small Redis stub."""

from __future__ import annotations

from typing import Any
from unittest import IsolatedAsyncioTestCase

from redis.exceptions import RedisError

from write_service.common.idempotency.atomic_redis.outcomes import (
    Acquired,
    AlreadyCompleted,
    InProgress,
    Mismatch,
)
from write_service.common.idempotency.atomic_redis.store import RedisIdempotencyStore
from write_service.common.idempotency.exceptions import StoreUnavailable


class _FakeRedis:
    """Mimics asyncio Redis: set(nx, ex), get, delete. Tracks calls for assertions."""

    def __init__(self) -> None:
        self.storage: dict[str, str] = {}
        self.set_calls: list[dict[str, Any]] = []
        self.delete_calls: list[str] = []
        self.raise_on_set = False
        self.raise_on_get = False
        self.raise_on_delete = False

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool | None:
        self.set_calls.append({"key": key, "value": value, "nx": nx, "ex": ex})
        if self.raise_on_set:
            raise RedisError("set failed")
        if nx and key in self.storage:
            return None
        self.storage[key] = value
        return True

    async def get(self, key: str) -> str | None:
        if self.raise_on_get:
            raise RedisError("get failed")
        return self.storage.get(key)

    async def delete(self, key: str) -> int:
        self.delete_calls.append(key)
        if self.raise_on_delete:
            raise RedisError("delete failed")
        return 1 if self.storage.pop(key, None) is not None else 0


class TryAcquireTests(IsolatedAsyncioTestCase):
    async def test_first_call_returns_acquired_and_stores_lock_payload(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        result = await store.try_acquire(user_id=1, idempotency_key="k", request_hash="h")

        self.assertIsInstance(result, Acquired)
        call = redis.set_calls[0]
        self.assertTrue(call["nx"])
        self.assertEqual(call["ex"], 30)
        self.assertIn('"state":"in_flight"', call["value"])
        self.assertIn('"request_hash":"h"', call["value"])

    async def test_default_key_prefix_is_applied(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        await store.try_acquire(user_id=42, idempotency_key="k1", request_hash="h")

        self.assertEqual(redis.set_calls[0]["key"], "idem:42:k1")

    async def test_custom_key_prefix_and_ttls_honored(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(
            redis,  # type: ignore[arg-type]
            key_prefix="ix-",
            lock_ttl_seconds=5,
            response_ttl_seconds=999,
        )

        await store.try_acquire(user_id="u", idempotency_key="k", request_hash="h")

        self.assertEqual(redis.set_calls[0]["key"], "ix-u:k")
        self.assertEqual(redis.set_calls[0]["ex"], 5)

    async def test_second_call_with_same_hash_returns_in_progress(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]
        await store.try_acquire(1, "k", "h")

        outcome = await store.try_acquire(1, "k", "h")

        self.assertIsInstance(outcome, InProgress)

    async def test_second_call_with_different_hash_returns_mismatch(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]
        await store.try_acquire(1, "k", "first-hash")

        outcome = await store.try_acquire(1, "k", "second-hash")

        self.assertIsInstance(outcome, Mismatch)
        assert isinstance(outcome, Mismatch)
        self.assertEqual(outcome.stored_hash, "first-hash")

    async def test_returns_already_completed_when_slot_holds_completed_entry(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]
        await store.store_response(
            user_id=1,
            idempotency_key="k",
            request_hash="h",
            status_code=201,
            body={"id": 1},
        )

        outcome = await store.try_acquire(1, "k", "h")

        self.assertIsInstance(outcome, AlreadyCompleted)
        assert isinstance(outcome, AlreadyCompleted)
        self.assertEqual(outcome.response.status_code, 201)
        self.assertEqual(outcome.response.body, {"id": 1})

    async def test_redis_error_on_acquire_raises_store_unavailable(self) -> None:
        redis = _FakeRedis()
        redis.raise_on_set = True
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        with self.assertRaises(StoreUnavailable):
            await store.try_acquire(1, "k", "h")

    async def test_redis_error_on_subsequent_get_raises_store_unavailable(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]
        await store.try_acquire(1, "k", "h")
        redis.raise_on_get = True

        with self.assertRaises(StoreUnavailable):
            await store.try_acquire(1, "k", "h")


class StoreResponseTests(IsolatedAsyncioTestCase):
    async def test_writes_completed_entry_with_response_ttl(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis, response_ttl_seconds=999)  # type: ignore[arg-type]

        await store.store_response(
            user_id=1,
            idempotency_key="k",
            request_hash="h",
            status_code=200,
            body={"ok": True},
            headers={"X-Foo": "bar"},
        )

        last_call = redis.set_calls[-1]
        self.assertEqual(last_call["ex"], 999)
        self.assertFalse(last_call["nx"])
        self.assertIn('"state":"completed"', last_call["value"])
        self.assertIn('"status_code":200', last_call["value"])

    async def test_headers_default_to_empty_dict(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        await store.store_response(
            user_id=1, idempotency_key="k", request_hash="h", status_code=200, body={}
        )

        self.assertIn('"headers":{}', redis.set_calls[-1]["value"])

    async def test_redis_error_on_store_raises_store_unavailable(self) -> None:
        redis = _FakeRedis()
        redis.raise_on_set = True
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        with self.assertRaises(StoreUnavailable):
            await store.store_response(
                user_id=1, idempotency_key="k", request_hash="h", status_code=200, body={}
            )


class ReleaseLockTests(IsolatedAsyncioTestCase):
    async def test_removes_slot_so_next_acquire_succeeds(self) -> None:
        redis = _FakeRedis()
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]
        await store.try_acquire(1, "k", "h")

        await store.release_lock(1, "k")
        next_acquire = await store.try_acquire(1, "k", "h")

        self.assertIsInstance(next_acquire, Acquired)
        self.assertIn("idem:1:k", redis.delete_calls)

    async def test_redis_error_on_release_is_swallowed(self) -> None:
        redis = _FakeRedis()
        redis.raise_on_delete = True
        store = RedisIdempotencyStore(redis)  # type: ignore[arg-type]

        await store.release_lock(1, "k")
