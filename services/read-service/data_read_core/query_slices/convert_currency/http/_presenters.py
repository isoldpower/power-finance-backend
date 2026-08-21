from typing import Any

from data_read_core.shared.exchange_rates import format_rate
from data_read_core.shared.money import money
from data_read_core.shared.timestamps import to_iso

from ..dtos import ConversionDTO


def present_conversion(conversion: ConversionDTO) -> dict[str, Any]:
    return {
        "from": money(conversion.from_amount, conversion.from_code, conversion.from_decimals),
        "to": money(conversion.to_amount, conversion.to_code, conversion.to_decimals),
        "rate": format_rate(conversion.rate),
    }


def present_meta(conversion: ConversionDTO) -> dict[str, Any]:
    return {"fetched_at": to_iso(conversion.fetched_at)}
