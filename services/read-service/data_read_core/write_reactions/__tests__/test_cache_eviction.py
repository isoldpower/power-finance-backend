from fakes import FakeRedis, make_event
from kafka_messages import TransactionDeleted, WalletDeleted

from data_read_core.write_reactions import EvictTransactionCache, EvictWalletCache
from data_read_core.write_reactions._cache_keys import (
    get_single_transaction_key,
    get_single_wallet_key,
)
from data_read_core.write_reactions.transaction_reactions import redis_single_evict as tx_evict
from data_read_core.write_reactions.wallet_reactions import redis_single_evict as wl_evict

WALLET_ID = "11111111-1111-1111-1111-111111111111"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


async def test_evicts_existing_transaction_key(monkeypatch):
    fake_redis = FakeRedis({get_single_transaction_key(TX_ID): "cached"})
    monkeypatch.setattr(tx_evict, "get_redis", lambda: fake_redis)

    await EvictTransactionCache().apply(make_event(TransactionDeleted(transaction_id=TX_ID)))

    assert get_single_transaction_key(TX_ID) not in fake_redis.store


async def test_transaction_evict_is_a_noop_when_absent(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(tx_evict, "get_redis", lambda: fake_redis)

    await EvictTransactionCache().apply(make_event(TransactionDeleted(transaction_id=TX_ID)))

    assert fake_redis.store == {}


async def test_evicts_existing_wallet_key(monkeypatch):
    fake_redis = FakeRedis({get_single_wallet_key(WALLET_ID): "cached"})
    monkeypatch.setattr(wl_evict, "get_redis", lambda: fake_redis)

    await EvictWalletCache().apply(make_event(WalletDeleted(wallet_id=WALLET_ID)))

    assert get_single_wallet_key(WALLET_ID) not in fake_redis.store


async def test_wallet_evict_leaves_unrelated_keys(monkeypatch):
    fake_redis = FakeRedis(
        {get_single_wallet_key(WALLET_ID): "cached", get_single_wallet_key("other"): "keep"}
    )
    monkeypatch.setattr(wl_evict, "get_redis", lambda: fake_redis)

    await EvictWalletCache().apply(make_event(WalletDeleted(wallet_id=WALLET_ID)))

    assert get_single_wallet_key("other") in fake_redis.store


async def test_a_transaction_against_a_goal_evicts_that_goal_key(monkeypatch):
    from kafka_messages import TransactionCreated

    from data_read_core.write_reactions import EvictGoalCacheForContainer
    from data_read_core.write_reactions._cache_keys import get_single_goal_key
    from data_read_core.write_reactions.goal_reactions import redis_single_evict as goal_evict

    goal_id = "9b65ffd3-3c69-407c-8e82-56a73cf6ffd3"
    fake_redis = FakeRedis(
        {get_single_goal_key(goal_id): "stale", get_single_goal_key("other"): "keep"}
    )
    monkeypatch.setattr(goal_evict, "get_redis", lambda: fake_redis)

    await EvictGoalCacheForContainer(TransactionCreated).apply(
        make_event(
            TransactionCreated(
                transaction_id=TX_ID,
                wallet_id=goal_id,
                user_id=7,
                amount="3.76",
                container_kind="goal",
            )
        )
    )

    assert get_single_goal_key(goal_id) not in fake_redis.store
    assert get_single_goal_key("other") in fake_redis.store


async def test_a_transaction_bumps_the_goal_list_version(monkeypatch):
    from kafka_messages import TransactionCreated

    from data_read_core.write_reactions import BumpGoalListVersion
    from data_read_core.write_reactions._cache_keys import get_goal_list_version_key
    from data_read_core.write_reactions.goal_reactions import redis_increase_version as goal_version

    fake_redis = FakeRedis()
    monkeypatch.setattr(goal_version, "get_redis", lambda: fake_redis)

    await BumpGoalListVersion(TransactionCreated).apply(
        make_event(
            TransactionCreated(
                transaction_id=TX_ID,
                wallet_id="9b65ffd3-3c69-407c-8e82-56a73cf6ffd3",
                user_id=7,
                amount="3.76",
                container_kind="goal",
            )
        )
    )

    assert fake_redis.store[get_goal_list_version_key(7)] == "1"
