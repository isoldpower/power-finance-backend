import json

from fakes import FakeRedis

from data_read_core.query_slices.get_transaction.cache_worker import CacheWorker
from data_read_core.query_slices.get_transaction.dtos import TransactionDTO
from data_read_core.query_slices.get_transaction.infra import (
    CACHE_TTL_SECONDS,
    get_single_cache_key,
)


def _transaction(transaction_id: str = "t1", user_id: int = 7) -> TransactionDTO:
    return TransactionDTO(
        id=transaction_id,
        user_id=user_id,
        wallet_id="w1",
        amount="100.00",
        currency="USD",
        occurred_at="2026-01-01T00:00:00+00:00",
        created_at="2026-01-01T00:00:00+00:00",
    )


async def test_miss_on_empty_store_returns_none(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    assert await worker.try_serve_from_cache("t1", user_id=7) is None


async def test_save_then_serve_round_trips(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    transaction = _transaction("t1", user_id=7)

    await worker.save_to_cache(transaction)
    served = await worker.try_serve_from_cache("t1", user_id=7)

    assert served == transaction


async def test_save_writes_single_key_with_ttl(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    await worker.save_to_cache(_transaction("t1"))

    assert len(fake_redis.set_calls) == 1
    key, raw_value, ttl = fake_redis.set_calls[0]
    assert key == get_single_cache_key("t1")
    assert ttl == CACHE_TTL_SECONDS
    assert json.loads(raw_value)["id"] == "t1"


async def test_foreign_owner_hit_is_evicted_and_misses(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    # cached entry owned by user 7
    await worker.save_to_cache(_transaction("t1", user_id=7))

    # a different user requesting the same transaction id must not see it
    served = await worker.try_serve_from_cache("t1", user_id=9)

    assert served is None
    # the stale foreign entry is dropped from the store
    assert get_single_cache_key("t1") not in fake_redis.store
