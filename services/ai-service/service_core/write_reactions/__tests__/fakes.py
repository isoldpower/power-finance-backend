"""The write-service messages these reactions are driven with.

Only protobuf lives here. A double standing in for a port belongs to the slice
that owns the port, not to a shared file that would have to import all four.
"""

from datetime import UTC, datetime
from uuid import UUID

from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import (
    TransactionCreated,
    TransactionDeleted,
    TransactionUpdated,
    UserSynced,
)

TRANSACTION_ID = UUID("11111111-1111-4111-8111-111111111111")
CONTAINER_ID = UUID("22222222-2222-4222-8222-222222222222")
USER_ID = 7
EXTERNAL_ID = "clerk_7"


def _timestamp(moment: datetime) -> Timestamp:
    stamp = Timestamp()
    stamp.FromDatetime(moment)
    return stamp


def make_transaction_created(
    *,
    transaction_id: UUID = TRANSACTION_ID,
    user_id: int = USER_ID,
    amount: str = "125.00",
    name: str = "Groceries",
    currency_code: str = "EUR",
) -> TransactionCreated:
    return TransactionCreated(
        event_id="evt-1",
        transaction_id=str(transaction_id),
        wallet_id=str(CONTAINER_ID),
        user_id=user_id,
        amount=amount,
        currency_code=currency_code,
        name=name,
        category="food",
        origin="manual",
        container_kind="wallet",
        created_at=_timestamp(datetime(2026, 8, 25, 12, 0, tzinfo=UTC)),
    )


def make_transaction_updated(
    *,
    transaction_id: UUID = TRANSACTION_ID,
    user_id: int = USER_ID,
    previous_amount: str = "125.00",
    new_amount: str = "200.00",
) -> TransactionUpdated:
    return TransactionUpdated(
        event_id="evt-2",
        transaction_id=str(transaction_id),
        wallet_id=str(CONTAINER_ID),
        user_id=user_id,
        previous_amount=previous_amount,
        new_amount=new_amount,
        updated_at=_timestamp(datetime(2026, 8, 25, 13, 0, tzinfo=UTC)),
    )


def make_transaction_deleted(
    *,
    transaction_id: UUID = TRANSACTION_ID,
    user_id: int = USER_ID,
) -> TransactionDeleted:
    return TransactionDeleted(
        event_id="evt-3",
        transaction_id=str(transaction_id),
        wallet_id=str(CONTAINER_ID),
        user_id=user_id,
        amount="125.00",
        created_at=_timestamp(datetime(2026, 8, 25, 12, 0, tzinfo=UTC)),
        deleted_at=_timestamp(datetime(2026, 8, 25, 14, 0, tzinfo=UTC)),
    )


def make_user_synced(*, user_id: int = USER_ID) -> UserSynced:
    return UserSynced(event_id="evt-0", user_id=user_id, external_id=f"clerk_{user_id}")
