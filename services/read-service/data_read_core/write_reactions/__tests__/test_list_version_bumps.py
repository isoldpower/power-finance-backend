from fakes import FakeRedis, make_event
from kafka_messages import TransactionCreated, WalletCreated, WalletUpdated

from data_read_core.write_reactions.transaction_reactions import (
    redis_increase_version as transaction_list_version,
)
from data_read_core.write_reactions.transaction_reactions.redis_increase_version import (
    BumpTransactionListVersion,
)
from data_read_core.write_reactions.wallet_reactions import (
    redis_increase_version as wallet_list_version,
)
from data_read_core.write_reactions.wallet_reactions.redis_increase_version import (
    BumpWalletListVersion,
)


async def test_wallet_bump_increments_per_user_counter(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(wallet_list_version, "get_redis", lambda: fake_redis)

    effect = BumpWalletListVersion(WalletCreated)
    await effect.apply(make_event(WalletCreated(user_id=7)))

    assert fake_redis.store["ver:wallets:7"] == "1"


async def test_wallet_bump_is_monotonic_across_events(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(wallet_list_version, "get_redis", lambda: fake_redis)

    await BumpWalletListVersion(WalletCreated).apply(make_event(WalletCreated(user_id=7)))
    await BumpWalletListVersion(WalletUpdated).apply(make_event(WalletUpdated(user_id=7)))

    assert fake_redis.store["ver:wallets:7"] == "2"


async def test_wallet_bump_isolates_users(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(wallet_list_version, "get_redis", lambda: fake_redis)

    await BumpWalletListVersion(WalletCreated).apply(make_event(WalletCreated(user_id=7)))

    assert fake_redis.store["ver:wallets:7"] == "1"
    assert "ver:wallets:9" not in fake_redis.store


async def test_transaction_bump_increments_transaction_namespace(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(transaction_list_version, "get_redis", lambda: fake_redis)

    effect = BumpTransactionListVersion(TransactionCreated)
    await effect.apply(make_event(TransactionCreated(user_id=9)))

    assert fake_redis.store["ver:transactions:9"] == "1"
    assert "ver:wallets:9" not in fake_redis.store
