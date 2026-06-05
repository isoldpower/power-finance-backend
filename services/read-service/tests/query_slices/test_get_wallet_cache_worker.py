import json

from data_read_core.query_slices.get_wallet.cache_worker import CacheWorker
from data_read_core.query_slices.get_wallet.dtos import WalletDTO
from data_read_core.query_slices.get_wallet.infra import (
    CACHE_TTL_SECONDS,
    get_single_cache_key,
)

from tests.fakes import FakeRedis


def _wallet(wallet_id: str = "w1", user_id: int = 7) -> WalletDTO:
    return WalletDTO(
        id=wallet_id,
        user_id=user_id,
        name="Main",
        balance_amount="100.00",
        currency="USD",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at=None,
    )


async def test_miss_on_empty_store_returns_none(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    assert await worker.try_serve_from_cache("w1", user_id=7) is None


async def test_save_then_serve_round_trips(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    wallet = _wallet("w1", user_id=7)

    await worker.save_to_cache(wallet)
    served = await worker.try_serve_from_cache("w1", user_id=7)

    assert served == wallet


async def test_save_writes_single_key_with_ttl(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    await worker.save_to_cache(_wallet("w1"))

    assert len(fake_redis.set_calls) == 1
    key, raw_value, ttl = fake_redis.set_calls[0]
    assert key == get_single_cache_key("w1")
    assert ttl == CACHE_TTL_SECONDS
    assert json.loads(raw_value)["id"] == "w1"


async def test_foreign_owner_hit_is_evicted_and_misses(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    # cached entry owned by user 7
    await worker.save_to_cache(_wallet("w1", user_id=7))

    # a different user requesting the same wallet id must not see it
    served = await worker.try_serve_from_cache("w1", user_id=9)

    assert served is None
    # the stale foreign entry is dropped from the store
    assert get_single_cache_key("w1") not in fake_redis.store
