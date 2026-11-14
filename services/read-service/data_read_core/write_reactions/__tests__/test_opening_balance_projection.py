from datetime import UTC, datetime, timedelta

import pytest
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import TransactionCreated

from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel
from data_read_core.write_reactions import CreateTransactionReadModel

pytestmark = pytest.mark.django_db(transaction=True)

WALLET_ID = "22222222-2222-2222-2222-222222222222"
TRANSACTION_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
WALLET_CREATED_AT = datetime(2026, 3, 1, 9, 30, 15, 123456, tzinfo=UTC)


def _timestamp(moment: datetime) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(moment)
    return timestamp


async def _project(created_at: datetime, chain_id: str = "") -> TransactionReadModel:
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=7,
        title="Everyday",
        currency_code="USD",
        created_at=WALLET_CREATED_AT,
    )
    await CreateTransactionReadModel().apply(
        make_event(
            TransactionCreated(
                transaction_id=TRANSACTION_ID,
                wallet_id=WALLET_ID,
                user_id=7,
                amount="2450.00",
                name="Opening balance",
                created_at=_timestamp(created_at),
                chain_id=chain_id,
            )
        )
    )

    return await TransactionReadModel.objects.aget(id=TRANSACTION_ID)


async def test_the_transaction_created_with_its_wallet_is_marked_as_the_opening_balance():
    projected = await _project(WALLET_CREATED_AT)

    assert projected.is_opening_balance is True


async def test_a_later_transaction_is_not_an_opening_balance():
    projected = await _project(WALLET_CREATED_AT + timedelta(microseconds=1))

    assert projected.is_opening_balance is False


async def test_a_transfer_leg_is_never_an_opening_balance():
    projected = await _project(WALLET_CREATED_AT, chain_id="cccccccc-cccc-cccc-cccc-cccccccccccc")

    assert projected.is_opening_balance is False
