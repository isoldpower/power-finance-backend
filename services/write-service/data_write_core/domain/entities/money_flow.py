from datetime import datetime
from uuid import UUID, uuid4

from ..events import EventCollector
from ..value_objects import MoneyFlowData
from ._entity_root import EntityRoot


class MoneyFlowEntity(EntityRoot, MoneyFlowData):
    _user_id: str
    _created_at: datetime

    def __init__(
        self,
        id: UUID,
        data: MoneyFlowData,
        user_id: str,
        created_at: datetime,
        event_collector: EventCollector,
    ):
        EntityRoot.__init__(self, unique_id=str(id), collector=event_collector)
        MoneyFlowData.__init__(
            self,
            transaction_id=data.transaction_id,
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

    @property
    def is_correction(self) -> bool:
        return self.cancels_other is not None or self.adjusts_other is not None

    @classmethod
    def create(
        cls,
        user_id: int,
        data: MoneyFlowData,
        created_at: datetime | None = None,
        _event_collector: EventCollector | None = None,
    ) -> "MoneyFlowEntity":
        return cls(
            id=uuid4(),
            data=data,
            user_id=str(user_id),
            created_at=created_at or datetime.now(),
            event_collector=_event_collector or EventCollector(),
        )

    @classmethod
    def from_persistence(
        cls,
        id: UUID,
        user_id: int,
        created_at: datetime,
        data: MoneyFlowData,
        _event_collector: EventCollector | None = None,
    ) -> "MoneyFlowEntity":
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
        created_at: datetime | None = None,
    ) -> "MoneyFlowEntity":
        return MoneyFlowEntity.create(
            user_id=int(self.user_id),
            created_at=created_at,
            data=MoneyFlowData(
                transaction_id=self.transaction_id,
                source_wallet_id=self.source_wallet_id,
                amount=-self.amount,
                cancels_other=UUID(self.unique_id),
            ),
            _event_collector=event_collector,
        )
