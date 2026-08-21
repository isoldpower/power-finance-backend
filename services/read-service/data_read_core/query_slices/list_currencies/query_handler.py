from data_read_core.shared.money import CURRENCY_CATALOG, CurrencyCatalog
from data_read_core.shared.query_results import FetchedRows

from .dtos import CurrencyDTO, ListCurrenciesQuery
from .logger_shortcuts import log_served_from_catalog


class ListCurrenciesQueryHandler:
    """No Redis cache worker here: the catalog already holds the table in
    process memory, so a network hop to Redis would be the slower path."""

    def __init__(self, catalog: CurrencyCatalog | None = None) -> None:
        self._catalog = catalog or CURRENCY_CATALOG

    async def handle(self, query: ListCurrenciesQuery) -> FetchedRows:
        records = await self._catalog.listing()
        currencies = [CurrencyDTO.from_record(record) for record in records]

        log_served_from_catalog(len(currencies))

        return FetchedRows(
            rows=currencies,
            total=len(currencies),
            cached=False,
        )
