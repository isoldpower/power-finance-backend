from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from kafka_messages_proto import WalletCreated, WalletDeleted, WalletUpdated

from ._outbox_event import OutboxEvent
from ._proto_utilities import format_timestamp_as_proto, to_proto_payload


@dataclass(frozen=True)
class WalletCreatedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "wallet"
    EVENT_TYPE: ClassVar[str] = "WalletCreated"
    SCHEMA_VERSION: ClassVar[int] = 1

    wallet_id: UUID
    user_id: int
    title: str
    currency_code: str
    created_at: datetime

    @property
    def aggregate_id(self) -> str:
        return str(self.wallet_id)

    def to_payload(self) -> dict[str, Any]:
        return to_proto_payload(
            WalletCreated(
                event_id=str(self.event_id),
                occurred_at=format_timestamp_as_proto(self.occurred_at),
                schema_version=self.SCHEMA_VERSION,
                wallet_id=str(self.wallet_id),
                user_id=self.user_id,
                title=self.title,
                currency_code=self.currency_code,
                created_at=format_timestamp_as_proto(self.created_at),
            )
        )


@dataclass(frozen=True)
class WalletDeletedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "wallet"
    EVENT_TYPE: ClassVar[str] = "WalletDeleted"
    SCHEMA_VERSION: ClassVar[int] = 1

    wallet_id: UUID
    user_id: int
    deleted_at: datetime

    @property
    def aggregate_id(self) -> str:
        return str(self.wallet_id)

    def to_payload(self) -> dict[str, Any]:
        return to_proto_payload(
            WalletDeleted(
                event_id=str(self.event_id),
                occurred_at=format_timestamp_as_proto(self.occurred_at),
                schema_version=self.SCHEMA_VERSION,
                wallet_id=str(self.wallet_id),
                user_id=self.user_id,
                deleted_at=format_timestamp_as_proto(self.deleted_at),
            )
        )


@dataclass(frozen=True)
class WalletUpdatedOutboxEvent(OutboxEvent):
    AGGREGATE_TYPE: ClassVar[str] = "wallet"
    EVENT_TYPE: ClassVar[str] = "WalletUpdated"
    SCHEMA_VERSION: ClassVar[int] = 1

    wallet_id: UUID
    user_id: int
    previous_title: str
    new_title: str
    updated_at: datetime

    @property
    def aggregate_id(self) -> str:
        return str(self.wallet_id)

    def to_payload(self) -> dict[str, Any]:
        return to_proto_payload(
            WalletUpdated(
                event_id=str(self.event_id),
                occurred_at=format_timestamp_as_proto(self.occurred_at),
                schema_version=self.SCHEMA_VERSION,
                wallet_id=str(self.wallet_id),
                user_id=self.user_id,
                previous_title=self.previous_title,
                new_title=self.new_title,
                updated_at=format_timestamp_as_proto(self.updated_at),
            )
        )
