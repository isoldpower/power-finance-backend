from datetime import datetime
from decimal import Decimal

from ..events import EventCollector
from ._entity_root import EntityRoot


class BalanceCheckpointEntity(EntityRoot):
    _created_at: datetime
    _balance: Decimal

    def __init__(
        self,
        id: str,
        created_at: datetime,
        balance: Decimal,
        event_collector: EventCollector | None = None,
    ):
        super().__init__(unique_id=id, collector=event_collector or EventCollector())

        self._created_at = created_at
        self._balance = balance

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def balance(self) -> Decimal:
        return self._balance
