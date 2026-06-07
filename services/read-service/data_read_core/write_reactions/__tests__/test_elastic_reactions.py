"""Elasticsearch projection effects — verified against a fake ES client.

These are pure projection effects: no DB except the transaction index, which
reads the owning wallet's currency. That lookup is stubbed so every case here
stays a unit test.
"""

from datetime import UTC, datetime

from fakes import FakeElasticsearch, make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import (
    TransactionCreated,
    TransactionDeleted,
    TransactionUpdated,
    WalletCreated,
    WalletDeleted,
    WalletUpdated,
)

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, WALLETS_INDEX
from data_read_core.write_reactions import (
    IndexTransactionDocument,
    IndexWalletDocument,
    RemoveTransactionDocument,
    RemoveWalletDocument,
    UpdateTransactionDocument,
    UpdateWalletDocument,
)
from data_read_core.write_reactions.transaction_reactions import (
    elastic_search_create as tx_create,
)
from data_read_core.write_reactions.transaction_reactions import (
    elastic_search_delete as tx_delete,
)
from data_read_core.write_reactions.transaction_reactions import (
    elastic_search_update as tx_update,
)
from data_read_core.write_reactions.wallet_reactions import (
    elastic_search_create as wl_create,
)
from data_read_core.write_reactions.wallet_reactions import (
    elastic_search_delete as wl_delete,
)
from data_read_core.write_reactions.wallet_reactions import (
    elastic_search_update as wl_update,
)

WALLET_ID = "11111111-1111-1111-1111-111111111111"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _ts() -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    return timestamp


def _use_fake_es(monkeypatch, module) -> FakeElasticsearch:
    fake = FakeElasticsearch()
    monkeypatch.setattr(module, "get_elasticsearch", lambda: fake)
    return fake


# --------------------------------------------------------------------------- #
# Transaction document projection
# --------------------------------------------------------------------------- #
async def test_index_transaction_writes_full_document(monkeypatch):
    fake = _use_fake_es(monkeypatch, tx_create)

    async def _currency(_wallet_id: str) -> str:
        return "EUR"

    monkeypatch.setattr(tx_create, "_wallet_currency", _currency)

    event = make_event(
        TransactionCreated(
            transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7, amount="25.50", created_at=_ts()
        )
    )
    await IndexTransactionDocument().apply(event)

    assert len(fake.indexed) == 1
    index, doc_id, document = fake.indexed[0]
    assert (index, doc_id) == (TRANSACTIONS_INDEX, TX_ID)
    assert document["amount"] == 25.5  # Decimal string coerced to float
    assert document["currency_code"] == "EUR"
    assert document["user_id"] == 7
    assert document["occurred_at"] == document["created_at"]


async def test_update_transaction_patches_amount_with_upsert(monkeypatch):
    fake = _use_fake_es(monkeypatch, tx_update)

    event = make_event(
        TransactionUpdated(transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7, new_amount="99.00")
    )
    await UpdateTransactionDocument().apply(event)

    assert len(fake.updated) == 1
    index, doc_id, doc, doc_as_upsert = fake.updated[0]
    assert (index, doc_id) == (TRANSACTIONS_INDEX, TX_ID)
    assert doc["amount"] == 99.0
    assert doc_as_upsert is True


async def test_remove_transaction_deletes_ignoring_404(monkeypatch):
    fake = _use_fake_es(monkeypatch, tx_delete)

    await RemoveTransactionDocument().apply(
        make_event(TransactionDeleted(transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7))
    )

    assert fake.deleted == [(TRANSACTIONS_INDEX, TX_ID)]
    assert fake.options_kwargs == [{"ignore_status": 404}]


# --------------------------------------------------------------------------- #
# Wallet document projection
# --------------------------------------------------------------------------- #
async def test_index_wallet_writes_full_document(monkeypatch):
    fake = _use_fake_es(monkeypatch, wl_create)

    event = make_event(
        WalletCreated(
            wallet_id=WALLET_ID, user_id=7, title="Vacation", currency_code="USD", created_at=_ts()
        )
    )
    await IndexWalletDocument().apply(event)

    assert len(fake.indexed) == 1
    index, doc_id, document = fake.indexed[0]
    assert (index, doc_id) == (WALLETS_INDEX, WALLET_ID)
    assert document["title"] == "Vacation"
    assert document["currency_code"] == "USD"
    assert document["balance"] == 0
    assert document["updated_at"] is None


async def test_update_wallet_patches_title_with_upsert(monkeypatch):
    fake = _use_fake_es(monkeypatch, wl_update)

    event = make_event(
        WalletUpdated(wallet_id=WALLET_ID, user_id=7, new_title="Renamed", updated_at=_ts())
    )
    await UpdateWalletDocument().apply(event)

    assert len(fake.updated) == 1
    index, doc_id, doc, doc_as_upsert = fake.updated[0]
    assert (index, doc_id) == (WALLETS_INDEX, WALLET_ID)
    assert doc["title"] == "Renamed"
    assert doc_as_upsert is True


async def test_remove_wallet_deletes_ignoring_404(monkeypatch):
    fake = _use_fake_es(monkeypatch, wl_delete)

    await RemoveWalletDocument().apply(make_event(WalletDeleted(wallet_id=WALLET_ID, user_id=7)))

    assert fake.deleted == [(WALLETS_INDEX, WALLET_ID)]
    assert fake.options_kwargs == [{"ignore_status": 404}]
