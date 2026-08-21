from data_read_core.shared.exchange_rates import ExchangeRateService, get_rate_service
from data_read_core.shared.money import CURRENCY_CATALOG, CurrencyCatalog

from .dtos import CurrencyRatesDTO, GetCurrencyRatesQuery
from .logger_shortcuts import log_rates_served


class GetCurrencyRatesQueryHandler:
    def __init__(
        self,
        rate_service: ExchangeRateService | None = None,
        catalog: CurrencyCatalog | None = None,
    ) -> None:
        self._rate_service = rate_service or get_rate_service()
        self._catalog = catalog or CURRENCY_CATALOG

    async def handle(self, query: GetCurrencyRatesQuery) -> CurrencyRatesDTO:
        base = await self._catalog.require(query.base_code)
        targets = await self._known_targets(query.target_codes)

        snapshot = await self._rate_service.snapshot_for(base.code)
        if targets is not None:
            snapshot = snapshot.only(targets)

        log_rates_served(base.code, len(snapshot.rates))

        return CurrencyRatesDTO(
            base=snapshot.base,
            rates=snapshot.rates,
            fetched_at=snapshot.fetched_at,
            requested_targets=targets,
        )

    async def _known_targets(self, target_codes: list[str] | None) -> list[str] | None:
        """Every requested code is checked against the table first, so an
        unknown one is a 422 rather than a silently missing map entry."""

        if target_codes is None:
            return None

        return [(await self._catalog.require(code)).code for code in target_codes]
