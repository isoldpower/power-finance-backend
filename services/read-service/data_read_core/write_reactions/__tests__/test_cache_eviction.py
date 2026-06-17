"""Single-entry cache eviction effects (transaction + wallet)."""

from fakes import FakeRedis, make_event
from kafka_messages import TransactionDeleted, WalletDeleted

from data_read_core.write_reactions import EvictTransactionCache, EvictWalletCache
from data_read_core.write_reactions.transaction_reactions import redis_single_evict as tx_evict
from data_read_core.write_reactions.wallet_reactions import redis_single_evict as wl_evict

WALLET_ID = "11111111-1111-1111-1111-111111111111"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


async def test_evicts_existing_transaction_key(monkeypatch):
    fake_redis = FakeRedis({f"read:transaction:{TX_ID}": "cached"})
    monkeypatch.setattr(tx_evict, "get_redis", lambda: fake_redis)

    await EvictTransactionCache().apply(make_event(TransactionDeleted(transaction_id=TX_ID)))

    assert f"read:transaction:{TX_ID}" not in fake_redis.store


async def test_transaction_evict_is_a_noop_when_absent(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(tx_evict, "get_redis", lambda: fake_redis)

    await EvictTransactionCache().apply(make_event(TransactionDeleted(transaction_id=TX_ID)))

    assert fake_redis.store == {}


async def test_evicts_existing_wallet_key(monkeypatch):
    fake_redis = FakeRedis({f"read:wallet:{WALLET_ID}": "cached"})
    monkeypatch.setattr(wl_evict, "get_redis", lambda: fake_redis)

    await EvictWalletCache().apply(make_event(WalletDeleted(wallet_id=WALLET_ID)))

    assert f"read:wallet:{WALLET_ID}" not in fake_redis.store


async def test_wallet_evict_leaves_unrelated_keys(monkeypatch):
    fake_redis = FakeRedis({f"read:wallet:{WALLET_ID}": "cached", "read:wallet:other": "keep"})
    monkeypatch.setattr(wl_evict, "get_redis", lambda: fake_redis)

    await EvictWalletCache().apply(make_event(WalletDeleted(wallet_id=WALLET_ID)))

    assert "read:wallet:other" in fake_redis.store
