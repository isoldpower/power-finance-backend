from datetime import UTC, datetime

import pytest
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import TransactionCreated

from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel
from data_read_core.write_reactions import CreateTransactionReadModel

WALLET_ID = "11111111-1111-1111-1111-111111111111"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _now_timestamp() -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime.now(UTC))
    return timestamp


def _transaction_created() -> TransactionCreated:
    return TransactionCreated(
        transaction_id=TX_ID,
        wallet_id=WALLET_ID,
        user_id=7,
        amount="25.00",
        created_at=_now_timestamp(),
    )


@pytest.mark.django_db(transaction=True)
async def test_currency_is_projected_from_owning_wallet():
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=7,
        title="Vacation",
        currency_code="EUR",
        balance=0,
        created_at=datetime.now(UTC),
        updated_at=None,
    )

    await CreateTransactionReadModel().apply(make_event(_transaction_created()))

    transaction = await TransactionReadModel.objects.aget(id=TX_ID)
    assert transaction.currency_code == "EUR"


@pytest.mark.django_db(transaction=True)
async def test_currency_degrades_to_empty_when_wallet_absent():
    # Wallet projection missing (out-of-order / dropped) — projection must still
    # land rather than fail, with currency left blank.
    await CreateTransactionReadModel().apply(make_event(_transaction_created()))

    transaction = await TransactionReadModel.objects.aget(id=TX_ID)
    assert transaction.currency_code == ""
