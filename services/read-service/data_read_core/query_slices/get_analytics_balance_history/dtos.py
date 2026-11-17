from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import ZERO, LedgerWallet, ScopedAnalyticsQuery


@dataclass(frozen=True)
class GetAnalyticsBalanceHistoryQuery(ScopedAnalyticsQuery):
    points: int

    @property
    def report_parameters(self) -> dict:
        return {"points": self.points}

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
            sum((series.converted_balances[index] for series in self.wallets), ZERO)
            for index in range(len(self.timestamps))
        ]
