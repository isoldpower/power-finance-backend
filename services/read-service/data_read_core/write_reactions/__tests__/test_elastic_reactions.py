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
from data_read_core.write_reactions.transaction_reactions._utilities import ContainerLabel
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
CHAIN_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _ts() -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    return timestamp


def _use_fake_es(monkeypatch, module) -> FakeElasticsearch:
    fake = FakeElasticsearch()
    monkeypatch.setattr(module, "get_elasticsearch", lambda: fake)
    return fake


async def test_index_transaction_writes_full_document(monkeypatch):
    fake = _use_fake_es(monkeypatch, tx_create)

    async def _label(_container_id: str, _kind: str | None = None) -> ContainerLabel:
        return ContainerLabel(currency_code="EUR", name="Random Credit Card", kind="wallet")

    monkeypatch.setattr(tx_create, "_container_label", _label)

    event = make_event(
        TransactionCreated(
            transaction_id=TX_ID,
            wallet_id=WALLET_ID,
            user_id=7,
            amount="-25.50",
            created_at=_ts(),
            name="Groceries store",
            category="Food",
            origin="manual",
        )
    )
    await IndexTransactionDocument().apply(event)

    assert len(fake.indexed) == 1
    index, doc_id, document = fake.indexed[0]
    assert (index, doc_id) == (TRANSACTIONS_INDEX, TX_ID)
    assert document["amount"] == -25.5
    assert document["currency_code"] == "EUR"
    assert document["wallet_name"] == "Random Credit Card"
    assert document["user_id"] == 7
    assert document["name"] == "Groceries store"
    assert document["category"] == "Food"
    assert document["occurred_at"] == document["created_at"]


async def test_indexed_type_is_read_off_the_sign(monkeypatch):
    """`type` is stored so search can filter on it, but it is never a second
    source of truth — it is derived from the amount at index time."""

    fake = _use_fake_es(monkeypatch, tx_create)

    async def _label(_container_id: str, _kind: str | None = None) -> ContainerLabel:
        return ContainerLabel(currency_code="EUR", name="Wallet", kind="wallet")

    monkeypatch.setattr(tx_create, "_container_label", _label)

    for amount, expected in (("-25.50", "expense"), ("25.50", "income")):
        await IndexTransactionDocument().apply(
            make_event(
                TransactionCreated(
                    transaction_id=TX_ID,
                    wallet_id=WALLET_ID,
                    user_id=7,
                    amount=amount,
                    created_at=_ts(),
                )
            )
        )
        assert fake.indexed[-1][2]["type"] == expected


async def test_a_chained_transaction_carries_its_chain_into_the_sort_column(monkeypatch):
    fake = _use_fake_es(monkeypatch, tx_create)

    async def _label(_container_id: str, _kind: str | None = None) -> ContainerLabel:
        return ContainerLabel(currency_code="EUR", name="Wallet", kind="wallet")

    monkeypatch.setattr(tx_create, "_container_label", _label)

    await IndexTransactionDocument().apply(
        make_event(
            TransactionCreated(
                transaction_id=TX_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                amount="-25.50",
                created_at=_ts(),
                chain_id=CHAIN_ID,
            )
        )
    )

    document = fake.indexed[-1][2]
    assert document["chain_id"] == CHAIN_ID
    assert document["chain_sort"] == CHAIN_ID


async def test_indexed_amount_survives_an_adjustment_in_the_same_type(monkeypatch):
    """Create and update must agree on how the amount is spelled, or the two
    reactions write different types into the same scaled_float field."""

    created = _use_fake_es(monkeypatch, tx_create)

    async def _label(_container_id: str, _kind: str | None = None) -> ContainerLabel:
        return ContainerLabel(currency_code="EUR", name="Wallet", kind="wallet")

    monkeypatch.setattr(tx_create, "_container_label", _label)
    await IndexTransactionDocument().apply(
        make_event(
            TransactionCreated(
                transaction_id=TX_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                amount="-25.50",
                created_at=_ts(),
            )
        )
    )

    updated = _use_fake_es(monkeypatch, tx_update)
    await UpdateTransactionDocument().apply(
        make_event(
            TransactionUpdated(
                transaction_id=TX_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                new_amount="-70.00",
            )
        )
    )

    indexed_amount = created.indexed[0][2]["amount"]
    patched_amount = updated.updated[0][2]["amount"]
    assert type(indexed_amount) is type(patched_amount)
    assert patched_amount == -70.0


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


async def test_remove_transaction_stamps_cancelled_ignoring_404(monkeypatch):
    """Cancelling keeps the document. Search hides it by filtering on
    `deleted_at`, so dropping it would lose the field that hides it."""

    fake = _use_fake_es(monkeypatch, tx_delete)

    await RemoveTransactionDocument().apply(
        make_event(
            TransactionDeleted(
                transaction_id=TX_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                deleted_at=_ts(),
            )
        )
    )

    assert fake.deleted == []
    assert fake.options_kwargs == [{"ignore_status": 404}]

    index, doc_id, doc, _ = fake.updated[0]
    assert (index, doc_id) == (TRANSACTIONS_INDEX, TX_ID)
    assert doc["deleted_at"] == "2026-01-02T03:04:05+00:00"


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


async def test_remove_wallet_stamps_closed_ignoring_404(monkeypatch):
    """Closing keeps the document. Search excludes closed wallets by filtering
    on `deleted_at`, so dropping it would lose the very field that hides it."""

    fake = _use_fake_es(monkeypatch, wl_delete)

    await RemoveWalletDocument().apply(
        make_event(WalletDeleted(wallet_id=WALLET_ID, user_id=7, deleted_at=_ts()))
    )

    assert fake.deleted == []
    assert fake.options_kwargs == [{"ignore_status": 404}]

    index, doc_id, doc, _ = fake.updated[0]
    assert (index, doc_id) == (WALLETS_INDEX, WALLET_ID)
    assert doc["deleted_at"] == "2026-01-02T03:04:05+00:00"
