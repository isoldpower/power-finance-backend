"""Postgres projection effects — exercised against the real read models.

Marked ``django_db(transaction=True)`` because the effects open
``aatomic()`` blocks and use ``select_for_update`` / ``F`` expressions that
must run on a real connection.
"""

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


# --------------------------------------------------------------------------- #
# Wallet read model
# --------------------------------------------------------------------------- #
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
    # No wallet projected yet — must not create one or raise.
    await UpdateWalletReadModel().apply(
        make_event(WalletUpdated(wallet_id=WALLET_ID, user_id=7, new_title="X", updated_at=_ts()))
    )

    assert not await WalletReadModel.objects.filter(id=WALLET_ID).aexists()


async def test_remove_wallet_deletes_row():
    await _make_wallet()

    await RemoveWalletReadModel().apply(make_event(WalletDeleted(wallet_id=WALLET_ID, user_id=7)))

    assert not await WalletReadModel.objects.filter(id=WALLET_ID).aexists()


# --------------------------------------------------------------------------- #
# Transaction read model — balance bookkeeping
# --------------------------------------------------------------------------- #
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
    assert wallet.balance == Decimal("130")  # 100 + (70 - 40)


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


async def test_remove_transaction_reverses_wallet_balance():
    await _make_wallet(balance=Decimal("100"))
    await _make_transaction(Decimal("40"))

    await RemoveTransactionReadModel().apply(
        make_event(TransactionDeleted(transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7))
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert not await TransactionReadModel.objects.filter(id=TX_ID).aexists()
    assert wallet.balance == Decimal("60")  # 100 - 40


async def test_remove_missing_transaction_is_a_noop():
    await _make_wallet(balance=Decimal("100"))

    await RemoveTransactionReadModel().apply(
        make_event(TransactionDeleted(transaction_id=TX_ID, wallet_id=WALLET_ID, user_id=7))
    )

    wallet = await WalletReadModel.objects.aget(id=WALLET_ID)
    assert wallet.balance == Decimal("100")  # untouched


# --------------------------------------------------------------------------- #
# User projection
# --------------------------------------------------------------------------- #
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
