from ..events import EventCollector
from ..value_objects import Currency
from ._entity_root import EntityRoot


class CurrencyEntity(EntityRoot):
    def __init__(
        self,
        currency_data: Currency,
        collector: EventCollector | None = None,
    ):
        super().__init__(
            unique_id=currency_data.code,
            collector=collector or EventCollector(),
        )
