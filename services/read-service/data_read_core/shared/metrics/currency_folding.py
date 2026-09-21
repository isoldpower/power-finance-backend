from collections.abc import Iterable, Mapping
from decimal import Decimal

from data_read_core.shared.exchange_rates import (
    ExchangeRateService,
    get_rate_service,
)

IDENTITY_RATE = Decimal(1)


class MoneyFolder:
    def __init__(
        self,
        target_currency: str,
        rate_service: ExchangeRateService | None = None,
    ) -> None:
        self._target = target_currency
        self._rate_service = rate_service
        self._rates: dict[str, Decimal] = {}

    async def prepare(self, currencies: Iterable[str]) -> None:
        for currency_code in set(currencies):
            await self._rate_for(currency_code)

    async def fold(self, subtotals: Mapping[str, Decimal]) -> Decimal:
        folder_total = Decimal(0)
        for currency_code, amount in subtotals.items():
            folder_total += amount * await self._rate_for(currency_code)

        return folder_total

    async def _rate_for(self, currency_code: str) -> Decimal:
        normalised = (currency_code or "").strip().upper()
        if not normalised or normalised == self._target:
            return IDENTITY_RATE

        if normalised not in self._rates:
            rate, _ = await self._rates_service().rate_between(
                normalised,
                self._target,
            )
            self._rates[normalised] = rate

        return self._rates[normalised]

    def _rates_service(self) -> ExchangeRateService:
        return self._rate_service or get_rate_service()
