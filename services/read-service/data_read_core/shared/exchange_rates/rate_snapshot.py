from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RateSnapshot:
    base: str
    rates: dict[str, Decimal]
    fetched_at: datetime

    def rate_to(self, currency_code: str) -> Decimal | None:
        return self.rates.get(currency_code.upper())

    def age(self, now: datetime | None = None) -> timedelta:
        return (now or datetime.now(UTC)) - self.fetched_at

    def is_fresh(self, max_age: timedelta, now: datetime | None = None) -> bool:
        return self.age(now) <= max_age

    def only(self, currency_codes: list[str]) -> "RateSnapshot":
        wanted = {code.upper() for code in currency_codes}

        return RateSnapshot(
            base=self.base,
            rates={code: rate for code, rate in self.rates.items() if code in wanted},
            fetched_at=self.fetched_at,
        )

    def to_cache(self) -> dict[str, Any]:
        return {
            "base": self.base,
            "rates": {code: str(rate) for code, rate in self.rates.items()},
            "fetched_at": self.fetched_at.isoformat(),
        }

    @classmethod
    def from_cache(cls, raw: dict[str, Any]) -> "RateSnapshot":
        return cls(
            base=raw["base"],
            rates={code: Decimal(rate) for code, rate in raw["rates"].items()},
            fetched_at=datetime.fromisoformat(raw["fetched_at"]),
        )
