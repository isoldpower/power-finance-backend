from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.exchange_rates import ExchangeRateService, get_rate_service
from data_read_core.shared.metrics import IDENTITY_RATE


@dataclass(frozen=True)
class RateTable:
    target_currency: str
    rates_to_target: dict[str, Decimal]

    def convert(self, amount: Decimal, currency: str) -> Decimal:
        return amount * self.rates_to_target.get(_normalised(currency), IDENTITY_RATE)


async def build_rate_table(
    target_currency: str,
    source_currencies: Iterable[str],
    rate_service: ExchangeRateService | None = None,
) -> RateTable:
    rates_to_target: dict[str, Decimal] = {}
    for source_currency in {_normalised(currency) for currency in source_currencies}:
        if not source_currency or source_currency == target_currency:
            continue

        rate, _ = await (rate_service or get_rate_service()).rate_between(
            source_currency,
            target_currency,
        )
        rates_to_target[source_currency] = rate

    return RateTable(target_currency=target_currency, rates_to_target=rates_to_target)


def _normalised(currency: str) -> str:
    return (currency or "").strip().upper()
