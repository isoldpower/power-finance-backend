from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import (
    TransactionDeleted,
    TransactionUpdated,
    UserSynced,
    WalletCreated,
    WalletDeleted,
    WalletUpdated,
)

from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel
from data_read_core.write_reactions import (
    CreateWalletReadModel,
    ProjectUserReadModel,
    RemoveTransactionReadModel,
    RemoveWalletReadModel,
    UpdateTransactionReadModel,
    UpdateWalletReadModel,
)

pytestmark = pytest.mark.django_db(transaction=True)

WALLET_ID = "11111111-1111-1111-1111-111111111111"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _ts(when: datetime | None = None) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(when or datetime.now(UTC))
    return timestamp


async def _make_wallet(*, balance: Decimal = Decimal("0"), currency: str = "USD") -> None:
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=7,
        title="Main",
        currency_code=currency,
        balance=balance,
        created_at=datetime.now(UTC),
        updated_at=None,
    )


async def _make_transaction(amount: Decimal) -> None:
    await TransactionReadModel.objects.acreate(
        id=TX_ID,
        wallet_id=WALLET_ID,
        user_id=7,
        amount=amount,
        currency_code="USD",
        occurred_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


async def test_create_wallet_projects_row():
    event = make_event(
        WalletCreated(
            wallet_id=WALLET_ID, user_id=7, title="Vacation", currency_code="EUR", created_at=_ts()
        )
    )
    await CreateWalletReadModel().apply(event)

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.title == "Vacation"
    assert wallet.currency_code == "EUR"
    assert wallet.balance == 0


async def test_update_wallet_changes_title():
    await _make_wallet()

    await UpdateWalletReadModel().apply(
        make_event(
            WalletUpdated(wallet_id=WALLET_ID, user_id=7, new_title="Renamed", updated_at=_ts())
        )
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.title == "Renamed"


async def test_update_missing_wallet_is_a_noop():
    await UpdateWalletReadModel().apply(
        make_event(WalletUpdated(wallet_id=WALLET_ID, user_id=7, new_title="X", updated_at=_ts()))
    )

    assert not await WalletReadModel.objects.filter(id=WALLET_ID).aexists()


async def test_remove_wallet_closes_row_without_dropping_it():
    """A closed wallet leaves lists and search but keeps existing — its
    transactions stay queryable and it still resolves by id."""

    await _make_wallet()

    await RemoveWalletReadModel().apply(
        make_event(
            WalletDeleted(
                wallet_id=WALLET_ID,
                user_id=7,
                deleted_at=_ts(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)),
            )
        )
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.deleted_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


async def test_update_transaction_adjusts_wallet_balance_by_delta():
    await _make_wallet(balance=Decimal("100"))
    await _make_transaction(Decimal("40"))

    await UpdateTransactionReadModel().apply(
        make_event(
            TransactionUpdated(
                transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7, new_amount="70"
            )
        )
    )

    transaction = await TransactionReadModel.objects.aget(id=TX_ID)
    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert transaction.amount == Decimal("70")
    assert wallet.balance == Decimal("130")


async def test_update_transaction_to_same_amount_leaves_balance():
    await _make_wallet(balance=Decimal("100"))
    await _make_transaction(Decimal("40"))

    await UpdateTransactionReadModel().apply(
        make_event(
            TransactionUpdated(
                transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7, new_amount="40"
            )
        )
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.balance == Decimal("100")


async def test_remove_transaction_cancels_it_and_reverses_the_balance():
    """The row survives with the amount it was FOR — that is what DELETE echoes
    back. Only the wallet balance moves, mirroring the inverse ledger flow."""

    await _make_wallet(balance=Decimal("100"))
    await _make_transaction(Decimal("40"))

    await RemoveTransactionReadModel().apply(
        make_event(
            TransactionDeleted(
                transaction_id=TX_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                deleted_at=_ts(datetime(2026, 2, 1, tzinfo=UTC)),
            )
        )
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    transaction = await TransactionReadModel.objects.aget(id=TX_ID)
    assert transaction.deleted_at == datetime(2026, 2, 1, tzinfo=UTC)
    assert transaction.amount == Decimal("40")
    assert wallet.balance == Decimal("60")


async def test_cancelling_twice_does_not_reverse_the_balance_twice():
    """A redelivered TransactionDeleted must not invent money."""

    await _make_wallet(balance=Decimal("100"))
    await _make_transaction(Decimal("40"))
    event = make_event(
        TransactionDeleted(
            transaction_id=TX_ID,
            wallet_id=WALLET_ID,
            user_id=7,
            deleted_at=_ts(datetime(2026, 2, 1, tzinfo=UTC)),
        )
    )

    await RemoveTransactionReadModel().apply(event)
    await RemoveTransactionReadModel().apply(event)

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.balance == Decimal("60")


async def test_remove_missing_transaction_is_a_noop():
    await _make_wallet(balance=Decimal("100"))

    await RemoveTransactionReadModel().apply(
        make_event(TransactionDeleted(transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7))
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.balance == Decimal("100")


async def test_project_user_creates_mapping():
    await ProjectUserReadModel().apply(make_event(UserSynced(user_id=7, external_id="ext-7")))

    user = await get_user_model().objects.aget(id=7)
    assert user.username == "ext-7"


async def test_project_user_is_idempotent_and_updates_external_id():
    await ProjectUserReadModel().apply(make_event(UserSynced(user_id=7, external_id="ext-7")))
    await ProjectUserReadModel().apply(make_event(UserSynced(user_id=7, external_id="ext-renamed")))

    user = await get_user_model().objects.aget(id=7)
    assert user.username == "ext-renamed"
    assert await get_user_model().objects.filter(id=7).acount() == 1
