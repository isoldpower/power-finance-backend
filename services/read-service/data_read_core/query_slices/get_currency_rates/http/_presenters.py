from typing import Any

from data_read_core.shared.exchange_rates import format_rate
from data_read_core.shared.timestamps import to_iso

from ..dtos import CurrencyRatesDTO


def present_rates(rates: CurrencyRatesDTO) -> dict[str, Any]:
    return {
        "base": rates.base,
        "rates": {code: format_rate(rate) for code, rate in sorted(rates.rates.items())},
    }


def present_meta(rates: CurrencyRatesDTO) -> dict[str, Any]:
    return {
        "fetched_at": to_iso(rates.fetched_at),
        "target": rates.requested_targets,
    }
