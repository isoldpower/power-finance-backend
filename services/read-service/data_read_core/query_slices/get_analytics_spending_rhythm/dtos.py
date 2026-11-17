from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import LedgerSide, ScopedAnalyticsQuery


@dataclass(frozen=True)
class GetAnalyticsSpendingRhythmQuery(ScopedAnalyticsQuery):
    side: LedgerSide

    @property
    def report_parameters(self) -> dict:
        return {"type": self.side.value}


@dataclass(frozen=True)
class RhythmCellDTO:
    iso_weekday: int
    hour: int
    amount: Decimal
    transactions_count: int


@dataclass(frozen=True)
class SpendingRhythmDTO:
    side: LedgerSide
    cells: list[RhythmCellDTO]

    @property
    def peak(self) -> RhythmCellDTO | None:
        peak_cell: RhythmCellDTO | None = None
        for cell in self.cells:
            if cell.amount > 0 and (peak_cell is None or cell.amount > peak_cell.amount):
                peak_cell = cell

        return peak_cell
