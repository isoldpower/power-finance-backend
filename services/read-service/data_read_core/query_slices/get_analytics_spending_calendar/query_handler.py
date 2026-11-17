from datetime import date

from data_read_core.shared.analytics import (
    AnalyticsLedger,
    AnalyticsReportHandler,
    FlowTally,
    build_days,
    local_moment,
)

from .config import REPORT_NAME
from .dtos import CalendarDayDTO, GetAnalyticsSpendingCalendarQuery, SpendingCalendarDTO


class GetAnalyticsSpendingCalendarQueryHandler(
    AnalyticsReportHandler[GetAnalyticsSpendingCalendarQuery]
):
    report_name = REPORT_NAME
    report_type = SpendingCalendarDTO

    async def _build(self, query: GetAnalyticsSpendingCalendarQuery) -> SpendingCalendarDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        zone = query.scope.zone
        tallies_by_date: dict[date, FlowTally] = {
            local_moment(day.start, zone).local_date: FlowTally()
            for day in build_days(query.scope.window, zone)
        }

        for row in await ledger.fetch_flows(query.scope.window, apply_categories=False):
            row_date = local_moment(row.created_at, zone).local_date
            if row_date not in tallies_by_date:
                continue

            tallies_by_date[row_date] = tallies_by_date[row_date].including(
                row.side,
                ledger.converted_magnitude(row),
            )

        return SpendingCalendarDTO(
            days=[
                CalendarDayDTO(
                    local_date=local_date,
                    inflow=tally.inflow,
                    outflow=tally.outflow,
                    transactions_count=tally.transactions_count,
                )
                for local_date, tally in tallies_by_date.items()
            ]
        )
