"""A provider that talks to nothing. For local work and tests."""

from datetime import UTC, datetime
from decimal import Decimal

from ..exceptions import RateUnavailable
from ..logger_shortcuts import log_static_provider_selected
from ..rate_snapshot import RateSnapshot
from .rate_provider import RateProvider

FIXED_USD_RATES: dict[str, Decimal] = {
    "USD": Decimal("1"),
    "EUR": Decimal("0.9"),
    "GBP": Decimal("0.8"),
    "JPY": Decimal("150"),
    "CHF": Decimal("0.88"),
    "CAD": Decimal("1.35"),
    "AUD": Decimal("1.5"),
    "CNY": Decimal("7.2"),
    "RUB": Decimal("82"),
    "INR": Decimal("83"),
    "PLN": Decimal("4"),
    "UAH": Decimal("41"),
}


class StaticRateProvider(RateProvider):
    name = "static"

    def __init__(self, rates: dict[str, Decimal] | None = None) -> None:
        self._usd_rates = dict(rates or FIXED_USD_RATES)
        log_static_provider_selected()

    async def fetch(self, base_code: str) -> RateSnapshot:
        base = base_code.upper()
        base_per_usd = self._usd_rates.get(base)
        if base_per_usd is None:
            raise RateUnavailable(f"Static rate table has no entry for {base}")

        return RateSnapshot(
            base=base,
            rates={code: rate / base_per_usd for code, rate in self._usd_rates.items()},
            fetched_at=datetime.now(UTC),
        )
