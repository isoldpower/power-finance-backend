import json

from fakes import FakeRedis

from data_read_core.query_slices.list_wallets.cache_worker import CacheWorker
from data_read_core.query_slices.list_wallets.dtos import (
    CacheOperationData,
    WalletDTO,
)
from data_read_core.query_slices.list_wallets.infra import (
    CACHE_TTL_SECONDS,
    get_filter_hash,
    get_list_cache_key,
    get_list_version_key,
)


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


def _operation(
    user_id: int = 7,
    filters: dict | None = None,
    limit: int = 20,
    offset: int = 0,
) -> CacheOperationData:
    return CacheOperationData(
        user_id=user_id,
        filters=filters if filters is not None else {},
        limit=limit,
        offset=offset,
    )


def _expected_key(operation: CacheOperationData, version: int) -> str:
    return get_list_cache_key(
        user_id=operation.user_id,
        version=version,
        filter_hash=get_filter_hash(operation.filters),
        limit=operation.limit,
        offset=operation.offset,
    )


async def test_miss_on_empty_store_returns_none(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)

    assert await worker.try_serve_from_cache(_operation()) is None


async def test_save_then_serve_round_trips(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    operation = _operation()
    wallets = [_wallet("w1"), _wallet("w2")]

    await worker.save_to_cache(context=operation, wallets=wallets, total=2)
    served = await worker.try_serve_from_cache(operation)

    assert served == (wallets, 2)


async def test_save_writes_versioned_key_with_ttl(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    operation = _operation(user_id=7, limit=10, offset=5)

    await worker.save_to_cache(context=operation, wallets=[_wallet()], total=1)

    expected_key = _expected_key(operation, version=0)
    assert len(fake_redis.set_calls) == 1
    key, raw_value, ttl = fake_redis.set_calls[0]
    assert key == expected_key
    assert ttl == CACHE_TTL_SECONDS
    payload = json.loads(raw_value)
    assert payload["total"] == 1
    assert payload["wallets"][0]["id"] == "w1"


async def test_version_bump_orphans_old_entry(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    operation = _operation(user_id=7)

    await worker.save_to_cache(context=operation, wallets=[_wallet()], total=1)
    assert await worker.try_serve_from_cache(operation) is not None

    fake_redis.store[get_list_version_key(7)] = "1"

    assert await worker.try_serve_from_cache(operation) is None


async def test_different_filters_use_distinct_keys(fake_redis: FakeRedis):
    worker = CacheWorker(fake_redis)
    no_filter = _operation(filters={})
    with_filter = _operation(filters={"currency": "USD"})

    await worker.save_to_cache(context=no_filter, wallets=[_wallet("a")], total=1)
    await worker.save_to_cache(context=with_filter, wallets=[_wallet("b")], total=1)

    served_no_filter = await worker.try_serve_from_cache(no_filter)
    served_with_filter = await worker.try_serve_from_cache(with_filter)

    assert served_no_filter[0][0].id == "a"
    assert served_with_filter[0][0].id == "b"
    assert len(fake_redis.set_calls) == 2
