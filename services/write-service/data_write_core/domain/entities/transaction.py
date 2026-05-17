from datetime import datetime
from uuid import UUID, uuid4

from ..events import EventCollector, TransactionCreatedEvent
from ..value_objects import TransactionData
from ._entity_root import EntityRoot


class TransactionEntity(EntityRoot, TransactionData):
    _user_id: str
    _created_at: datetime

    def __init__(
        self,
        id: UUID,
        data: TransactionData,
        user_id: str,
        created_at: datetime,
        event_collector: EventCollector,
    ):
        EntityRoot.__init__(self, unique_id=str(id), collector=event_collector)
        TransactionData.__init__(
            self,
            source_wallet_id=data.source_wallet_id,
            amount=data.amount,
            cancels_other=data.cancels_other,
            adjusts_other=data.adjusts_other,
        )

        self._user_id = user_id
        self._created_at = created_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def user_id(self) -> str:
        return self._user_id

    @classmethod
    def create(
        cls,
        user_id: int,
        data: TransactionData,
        _event_collector: EventCollector | None = None,
    ) -> "TransactionEntity":
        created_transaction = cls(
            id=uuid4(),
            data=data,
            user_id=str(user_id),
            created_at=datetime.now(),
            event_collector=_event_collector or EventCollector(),
        )

        created_transaction.events_occurred(
            TransactionCreatedEvent(
                transaction_id=UUID(created_transaction.unique_id),
                wallet_id=created_transaction.source_wallet_id,
                created_at=created_transaction.created_at,
                user_id=int(created_transaction.user_id),
                amount=created_transaction.amount,
            )
        )

        return created_transaction

    @classmethod
    def from_persistence(
        cls,
        id: UUID,
        user_id: int,
        created_at: datetime,
        data: TransactionData,
        _event_collector: EventCollector | None = None,
    ) -> "TransactionEntity":
        return cls(
            id=id,
            data=data,
            user_id=str(user_id),
            created_at=created_at,
            event_collector=_event_collector or EventCollector(),
        )

    def create_inverse(
        self,
        event_collector: EventCollector | None = None,
    ) -> "TransactionEntity":
        return TransactionEntity.create(
            user_id=int(self.user_id),
            data=TransactionData(
                source_wallet_id=self.source_wallet_id,
                amount=-self.amount,
                cancels_other=UUID(self.unique_id),
                adjusts_other=None,
            ),
            _event_collector=event_collector,
        )
