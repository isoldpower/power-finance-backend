from datetime import date

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    LedgerSide,
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
        days_by_date: dict[date, CalendarDayDTO] = {
            local_moment(day.start, zone).local_date: CalendarDayDTO(
                local_date=local_moment(day.start, zone).local_date,
                inflow=ZERO,
                outflow=ZERO,
                transactions_count=0,
            )
            for day in build_days(query.scope.window, zone)
        }

        for row in await ledger.fetch_flows(query.scope.window, apply_categories=False):
            row_date = local_moment(row.created_at, zone).local_date
            current_day = days_by_date.get(row_date)
            if current_day is None:
                continue

            converted_amount = ledger.converted_magnitude(row)
            days_by_date[row_date] = CalendarDayDTO(
                local_date=row_date,
                inflow=current_day.inflow
                + (converted_amount if row.side is LedgerSide.INCOME else ZERO),
                outflow=current_day.outflow
                + (converted_amount if row.side is LedgerSide.EXPENSE else ZERO),
                transactions_count=current_day.transactions_count + 1,
            )

        return SpendingCalendarDTO(days=list(days_by_date.values()))
