from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import SECONDS_PER_DAY, ReservedTokens
from .ledger_rows import AnalyticsCategory


@dataclass(frozen=True)
class AnalyticsWindow:
    since: datetime
    until: datetime

    @property
    def length(self) -> timedelta:
        return self.until - self.since

    @property
    def previous(self) -> "AnalyticsWindow":
        return AnalyticsWindow(since=self.since - self.length, until=self.since)

    @property
    def whole_day_count(self) -> int:
        return max(1, round(self.length.total_seconds() / SECONDS_PER_DAY))

    def contains(self, moment: datetime) -> bool:
        return self.since <= moment < self.until


@dataclass(frozen=True)
class AnalyticsScope:
    user_id: int
    window: AnalyticsWindow
    currency: str
    timezone: str
    wallet_identifiers: tuple[str, ...] | None
    categories: tuple[AnalyticsCategory | None, ...] | None

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def category_tokens(self) -> list[str] | None:
        if self.categories is None:
            return None

        return [category_token(category) for category in self.categories]

    @property
    def cache_signature(self) -> dict:
        category_tokens = self.category_tokens

        return {
            "since": self.window.since.isoformat(),
            "until": self.window.until.isoformat(),
            "currency": self.currency,
            "timezone": self.timezone,
            "wallets": sorted(self.wallet_identifiers) if self.wallet_identifiers else None,
            "categories": sorted(category_tokens) if category_tokens else None,
        }


def category_token(category: AnalyticsCategory | None) -> str:
    return ReservedTokens.UNCATEGORISED.value if category is None else category.identifier
