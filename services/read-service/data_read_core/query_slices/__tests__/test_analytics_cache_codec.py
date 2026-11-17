import json
from datetime import UTC, date, datetime
from decimal import Decimal

from data_read_core.query_slices.get_analytics_overview.dtos import (
    OverviewDTO,
    PeriodSummaryDTO,
    TopCategoryDTO,
)
from data_read_core.query_slices.get_analytics_spending_calendar.dtos import (
    CalendarDayDTO,
    SpendingCalendarDTO,
)
from data_read_core.shared.analytics import (
    AnalyticsCategory,
    LedgerSide,
    LedgerWallet,
    TransactionBriefDTO,
    decode_from_cache,
    encode_for_cache,
)

WALLET = LedgerWallet(identifier="w-1", name="Cash", color="#000", currency="USD", favorite=True)


def _round_trip(report_type: type, report):
    return decode_from_cache(report_type, json.loads(json.dumps(encode_for_cache(report))))


def _summary(largest_expense: TransactionBriefDTO | None) -> PeriodSummaryDTO:
    return PeriodSummaryDTO(
        since=datetime(2026, 3, 1, tzinfo=UTC),
        until=datetime(2026, 3, 8, tzinfo=UTC),
        inflow=Decimal("500.00"),
        outflow=Decimal("300.00"),
        savings_rate=Decimal("40.00"),
        transactions_count=5,
        active_days=4,
        average_daily_outflow=Decimal("42.857142"),
        largest_expense=largest_expense,
        largest_income=None,
        top_expense_category=TopCategoryDTO(category=None, amount=Decimal("1"), share=Decimal("2")),
    )


def test_nested_reports_survive_the_cache_unchanged():
    brief = TransactionBriefDTO(
        identifier="t-1",
        name="Rent",
        created_at=datetime(2026, 3, 4, 10, tzinfo=UTC),
        side=LedgerSide.EXPENSE,
        category=AnalyticsCategory(identifier="c-1", name="Rent", is_global=False),
        wallet=WALLET,
        native_amount=Decimal("108.00"),
        native_currency="EUR",
        converted_amount=Decimal("120.00"),
    )
    overview = OverviewDTO(current=_summary(brief), previous=_summary(None))

    assert _round_trip(OverviewDTO, overview) == overview


def test_dates_and_lists_survive_the_cache_unchanged():
    calendar = SpendingCalendarDTO(
        days=[
            CalendarDayDTO(
                local_date=date(2026, 3, 1),
                inflow=Decimal("0"),
                outflow=Decimal("12.50"),
                transactions_count=1,
            )
        ]
    )

    assert _round_trip(SpendingCalendarDTO, calendar) == calendar
