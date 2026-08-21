from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ConvertCurrencyQuery:
    from_code: str
    to_code: str
    raw_amount: object


@dataclass(frozen=True)
class ConversionDTO:
    from_code: str
    from_amount: Decimal
    from_decimals: int
    to_code: str
    to_amount: Decimal
    to_decimals: int
    rate: Decimal
    fetched_at: datetime
