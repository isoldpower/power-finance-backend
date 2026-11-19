from decimal import Decimal
from typing import NamedTuple

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    local_moment,
)

from .config import HOURS_OF_DAY, ISO_WEEKDAYS, REPORT_NAME
from .dtos import GetAnalyticsSpendingRhythmQuery, RhythmCellDTO, SpendingRhythmDTO


class CellPosition(NamedTuple):
    iso_weekday: int
    hour: int


class GetAnalyticsSpendingRhythmQueryHandler(
    AnalyticsReportHandler[GetAnalyticsSpendingRhythmQuery]
):
    report_name = REPORT_NAME
    report_type = SpendingRhythmDTO

    async def _build(self, query: GetAnalyticsSpendingRhythmQuery) -> SpendingRhythmDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        amounts_by_cell: dict[CellPosition, Decimal] = {}
        counts_by_cell: dict[CellPosition, int] = {}

        rows = await ledger.fetch_flows(query.scope.window, side=query.side, apply_categories=False)
        for row in rows:
            moment = local_moment(row.created_at, query.scope.zone)
            cell_position = CellPosition(iso_weekday=moment.iso_weekday, hour=moment.hour)
            amounts_by_cell[cell_position] = amounts_by_cell.get(
                cell_position, ZERO
            ) + ledger.converted_magnitude(row)
            counts_by_cell[cell_position] = counts_by_cell.get(cell_position, 0) + 1

        return SpendingRhythmDTO(
            side=query.side,
            cells=[
                RhythmCellDTO(
                    iso_weekday=iso_weekday,
                    hour=hour,
                    amount=amounts_by_cell.get(CellPosition(iso_weekday, hour), ZERO),
                    transactions_count=counts_by_cell.get(CellPosition(iso_weekday, hour), 0),
                )
                for iso_weekday in ISO_WEEKDAYS
                for hour in HOURS_OF_DAY
            ],
        )
