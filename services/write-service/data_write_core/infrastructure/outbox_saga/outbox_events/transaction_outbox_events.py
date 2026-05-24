from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from kafka_messages import TransactionCreated, TransactionDeleted

from ._outbox_event import OutboxEvent
from ._proto_utilities import format_timestamp_as_proto, to_proto_payload


@dataclass(frozen=True)
class TransactionCreatedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "transaction"
    EVENT_TYPE: ClassVar[str] = "TransactionCreated"
    SCHEMA_VERSION: ClassVar[int] = 1

    transaction_id: UUID
    wallet_id: UUID
    user_id: int
    amount: Decimal
    created_at: datetime

    @property
    def aggregate_id(self) -> str:
        return str(self.transaction_id)

    def to_payload(self) -> dict[str, Any]:
        return to_proto_payload(
            TransactionCreated(
                event_id=str(self.event_id),
                occurred_at=format_timestamp_as_proto(self.occurred_at),
                schema_version=self.SCHEMA_VERSION,
                transaction_id=str(self.transaction_id),
                wallet_id=str(self.wallet_id),
                user_id=self.user_id,
                amount=str(self.amount),
                created_at=format_timestamp_as_proto(self.created_at),
            )
        )


@dataclass(frozen=True)
class TransactionDeletedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "transaction"
    EVENT_TYPE: ClassVar[str] = "TransactionDeleted"
    SCHEMA_VERSION: ClassVar[int] = 1

    transaction_id: UUID
    wallet_id: UUID
    user_id: int
    amount: Decimal
    cancelled_by: UUID
    created_at: datetime

    @property
    def aggregate_id(self) -> str:
        return str(self.transaction_id)

    def to_payload(self) -> dict[str, Any]:
        return to_proto_payload(
            TransactionDeleted(
                event_id=str(self.event_id),
                occurred_at=format_timestamp_as_proto(self.occurred_at),
                schema_version=self.SCHEMA_VERSION,
                transaction_id=str(self.transaction_id),
                wallet_id=str(self.wallet_id),
                user_id=self.user_id,
                amount=str(self.amount),
                cancelled_by=str(self.cancelled_by),
                created_at=format_timestamp_as_proto(self.created_at),
            )
        )
