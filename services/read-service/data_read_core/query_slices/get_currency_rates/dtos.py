from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class GetCurrencyRatesQuery:
    base_code: str
    target_codes: list[str] | None = None


@dataclass(frozen=True)
class CurrencyRatesDTO:
    base: str
    rates: dict[str, Decimal]
    fetched_at: datetime
    requested_targets: list[str] | None
