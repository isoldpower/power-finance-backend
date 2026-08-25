from decimal import Decimal
from typing import Protocol, runtime_checkable

from ..entities import MoneyFlowEntity
from ..value_objects import MoneyContainerRef


@runtime_checkable
class MoneyContainerAggregate(Protocol):
    @property
    def unique_id(self) -> str: ...

    @property
    def currency_code(self) -> str: ...

    @property
    def balance(self) -> Decimal: ...

    @property
    def is_closed(self) -> bool: ...

    def record(self, flow: MoneyFlowEntity) -> None: ...

    def as_reference(self) -> MoneyContainerRef: ...
