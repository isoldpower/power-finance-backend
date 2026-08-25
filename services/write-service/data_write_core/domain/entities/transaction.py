from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..events import EventCollector
from ..value_objects import (
    MoneyContainerKind,
    TransactionMetadata,
    TransactionOrigin,
    TransactionType,
)
from ._entity_root import EntityRoot

UNCHANGED = object()


class TransactionEntity(EntityRoot, TransactionMetadata):
    _user_id: str
    _container_id: UUID
    _container_kind: MoneyContainerKind
    _created_at: datetime
    _updated_at: datetime | None
    _deleted_at: datetime | None

    def __init__(
        self,
        id: UUID,
        user_id: str,
        container_id: UUID,
        container_kind: MoneyContainerKind,
        metadata: TransactionMetadata,
        created_at: datetime,
        event_collector: EventCollector,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        EntityRoot.__init__(self, unique_id=str(id), collector=event_collector)
        TransactionMetadata.__init__(
            self,
            name=metadata.name,
            category=metadata.category,
            evidence_url=metadata.evidence_url,
            origin=metadata.origin,
            chain_id=metadata.chain_id,
        )

        self._user_id = user_id
        self._container_id = container_id
        self._container_kind = container_kind
        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def container_id(self) -> UUID:
        return self._container_id

    @property
    def container_kind(self) -> MoneyContainerKind:
        return self._container_kind

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    def mark_cancelled(self, now: datetime) -> None:
        self._deleted_at = now
        self._updated_at = now

    def restore(self, now: datetime) -> None:
        self._deleted_at = None
        self._updated_at = now

    def snapshot(self) -> TransactionMetadata:
        return TransactionMetadata(
            name=self.name,
            category=self.category,
            evidence_url=self.evidence_url,
            origin=self.origin,
            chain_id=self.chain_id,
        )

    def apply(self, metadata: TransactionMetadata, now: datetime) -> None:
        self.name = metadata.name
        self.category = metadata.category
        self.evidence_url = metadata.evidence_url
        self._updated_at = now

    def update_metadata(
        self,
        now: datetime,
        name: str | object = UNCHANGED,
        category: str | None | object = UNCHANGED,
        evidence_url: str | None | object = UNCHANGED,
    ) -> bool:
        changed = False
        for field, value in (
            ("name", name),
            ("category", category),
            ("evidence_url", evidence_url),
        ):
            if value is UNCHANGED or getattr(self, field) == value:
                continue

            setattr(self, field, value)
            changed = True

        if changed:
            self._updated_at = now

        return changed

    @staticmethod
    def type_for(amount: Decimal) -> TransactionType:
        return TransactionType.EXPENSE if amount < 0 else TransactionType.INCOME

    @staticmethod
    def signed(amount: Decimal, transaction_type: TransactionType) -> Decimal:
        magnitude = abs(amount)

        return -magnitude if transaction_type is TransactionType.EXPENSE else magnitude

    @classmethod
    def create(
        cls,
        id: UUID,
        user_id: int,
        container_id: UUID,
        container_kind: MoneyContainerKind,
        metadata: TransactionMetadata,
        created_at: datetime,
        _event_collector: EventCollector | None = None,
    ) -> "TransactionEntity":
        return cls(
            id=id,
            user_id=str(user_id),
            container_id=container_id,
            container_kind=container_kind,
            metadata=metadata,
            created_at=created_at,
            event_collector=_event_collector or EventCollector(),
        )


__all__ = [
    "UNCHANGED",
    "MoneyContainerKind",
    "TransactionEntity",
    "TransactionOrigin",
    "TransactionType",
]
