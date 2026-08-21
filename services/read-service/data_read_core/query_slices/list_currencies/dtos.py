from dataclasses import dataclass

from data_read_core.shared.money import CurrencyRecord


@dataclass(frozen=True)
class ListCurrenciesQuery:
    """No user, no filters, no page. The table is the same for everyone."""


@dataclass(frozen=True)
class CurrencyDTO:
    code: str
    symbol: str
    name: str
    decimals: int

    @classmethod
    def from_record(cls, record: CurrencyRecord) -> "CurrencyDTO":
        return cls(
            code=record.code,
            symbol=record.symbol,
            name=record.name,
            decimals=record.digits,
        )
