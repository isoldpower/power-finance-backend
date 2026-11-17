from decimal import Decimal

from data_read_core.shared.analytics import (
    AnalyticsLedger,
    AnalyticsReportHandler,
    AnalyticsWindow,
    LedgerRow,
    LedgerSide,
    TransactionBriefDTO,
    brief_of,
    local_moment,
    savings_rate_of,
    share_of,
    tally_by_category,
)

from .config import REPORT_NAME
from .dtos import GetAnalyticsOverviewQuery, OverviewDTO, PeriodSummaryDTO, TopCategoryDTO


class GetAnalyticsOverviewQueryHandler(AnalyticsReportHandler[GetAnalyticsOverviewQuery]):
    report_name = REPORT_NAME
    report_type = OverviewDTO

    async def _build(self, query: GetAnalyticsOverviewQuery) -> OverviewDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)

        return OverviewDTO(
            current=await _summarise(ledger, query.scope.window),
            previous=await _summarise(ledger, query.scope.window.previous),
        )


async def _summarise(ledger: AnalyticsLedger, window: AnalyticsWindow) -> PeriodSummaryDTO:
    rows = await ledger.fetch_flows(window)
    expense_rows = [row for row in rows if row.side is LedgerSide.EXPENSE]
    income_rows = [row for row in rows if row.side is LedgerSide.INCOME]
    inflow = ledger.converted_total(income_rows)
    outflow = ledger.converted_total(expense_rows)

    return PeriodSummaryDTO(
        since=window.since,
        until=window.until,
        inflow=inflow,
        outflow=outflow,
        savings_rate=savings_rate_of(inflow, outflow),
        transactions_count=len(rows),
        active_days=len(
            {local_moment(row.created_at, ledger.scope.zone).local_date for row in rows}
        ),
        average_daily_outflow=outflow / window.whole_day_count,
        largest_expense=_largest_brief(ledger, expense_rows),
        largest_income=_largest_brief(ledger, income_rows),
        top_expense_category=_top_category(ledger, expense_rows, outflow),
    )


def _largest_brief(ledger: AnalyticsLedger, rows: list[LedgerRow]) -> TransactionBriefDTO | None:
    largest_row = max(rows, key=ledger.converted_magnitude, default=None)
    if largest_row is None:
        return None

    return brief_of(largest_row, ledger)


def _top_category(
    ledger: AnalyticsLedger,
    expense_rows: list[LedgerRow],
    outflow: Decimal,
) -> TopCategoryDTO | None:
    if outflow == 0:
        return None

    top_tally = tally_by_category(ledger, expense_rows)[0]

    return TopCategoryDTO(
        category=top_tally.category,
        amount=top_tally.amount,
        share=share_of(top_tally.amount, outflow),
    )
