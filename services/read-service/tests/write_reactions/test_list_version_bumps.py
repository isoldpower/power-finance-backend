from data_read_core.write_reactions.transaction_reactions import (
    transaction_list_version,
)
from data_read_core.write_reactions.transaction_reactions.transaction_list_version import (
    BumpTransactionListVersion,
)
from data_read_core.write_reactions.wallet_reactions import wallet_list_version
from data_read_core.write_reactions.wallet_reactions.wallet_list_version import (
    BumpWalletListVersion,
)
from kafka_messages import TransactionCreated, WalletCreated, WalletUpdated

from tests.fakes import FakeRedis, make_event


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
