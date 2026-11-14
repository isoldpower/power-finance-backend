from collections import defaultdict
from decimal import Decimal

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    AnalyticsWindow,
    LedgerRow,
    LedgerSide,
    brief_of,
    local_moment,
    savings_rate_of,
    share_of,
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
    inflow = _converted_total(ledger, income_rows)
    outflow = _converted_total(ledger, expense_rows)
    largest_expense = _largest(ledger, expense_rows)
    largest_income = _largest(ledger, income_rows)

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
        largest_expense=brief_of(largest_expense, ledger) if largest_expense else None,
        largest_income=brief_of(largest_income, ledger) if largest_income else None,
        top_expense_category=_top_category(ledger, expense_rows, outflow),
    )


def _converted_total(ledger: AnalyticsLedger, rows: list[LedgerRow]) -> Decimal:
    return sum((ledger.converted_magnitude(row) for row in rows), ZERO)


def _largest(ledger: AnalyticsLedger, rows: list[LedgerRow]) -> LedgerRow | None:
    largest_row: LedgerRow | None = None
    largest_amount = ZERO
    for row in rows:
        converted_amount = ledger.converted_magnitude(row)
        if largest_row is None or converted_amount > largest_amount:
            largest_row = row
            largest_amount = converted_amount

    return largest_row


def _top_category(
    ledger: AnalyticsLedger,
    expense_rows: list[LedgerRow],
    outflow: Decimal,
) -> TopCategoryDTO | None:
    if outflow == 0:
        return None

    totals_by_category: dict[str | None, Decimal] = defaultdict(lambda: ZERO)
    for row in expense_rows:
        totals_by_category[row.category] += ledger.converted_magnitude(row)

    top_category, top_amount = max(
        totals_by_category.items(),
        key=lambda category_total: category_total[1],
    )

    return TopCategoryDTO(
        category=top_category,
        amount=top_amount,
        share=share_of(top_amount, outflow),
    )
