from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, LedgerWallet


@dataclass(frozen=True)
class GetAnalyticsBalanceHistoryQuery:
    scope: AnalyticsScope
    points: int

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {**self.scope.cache_signature, "points": self.points}

    @property
    def sample_instants(self) -> list[datetime]:
        window = self.scope.window
        step = window.length / (self.points - 1)

        return [
            window.until if index == self.points - 1 else window.since + step * index
            for index in range(self.points)
        ]


@dataclass(frozen=True)
class WalletBalanceSeriesDTO:
    wallet: LedgerWallet
    converted_balances: list[Decimal]
    native_balances: list[Decimal]


@dataclass(frozen=True)
class BalanceHistoryDTO:
    timestamps: list[datetime]
    wallets: list[WalletBalanceSeriesDTO]

    @property
    def totals(self) -> list[Decimal]:
        return [
            sum((series.converted_balances[index] for series in self.wallets), Decimal(0))
            for index in range(len(self.timestamps))
        ]
