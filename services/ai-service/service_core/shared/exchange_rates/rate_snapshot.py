from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
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
