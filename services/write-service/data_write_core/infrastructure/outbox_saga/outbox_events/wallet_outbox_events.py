from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from ._outbox_event import OutboxEvent


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
        return {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "wallet_id": str(self.wallet_id),
            "user_id": self.user_id,
            "title": self.title,
            "currency_code": self.currency_code,
            "created_at": self.created_at.isoformat(),
        }


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
        return {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "wallet_id": str(self.wallet_id),
            "user_id": self.user_id,
            "deleted_at": self.deleted_at.isoformat(),
        }


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
        return {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "wallet_id": str(self.wallet_id),
            "user_id": self.user_id,
            "previous_title": self.previous_title,
            "new_title": self.new_title,
            "updated_at": self.updated_at.isoformat(),
        }
