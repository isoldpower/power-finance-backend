from data_read_core.shared.analytics import (
    AnalyticsScope,
    as_percentage,
    present_analytics_category,
    present_optional_transaction_brief,
    present_scope_meta,
)
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..dtos import OverviewDTO, PeriodSummaryDTO, TopCategoryDTO


async def present_overview(overview: OverviewDTO, currency: str) -> dict:
    return {
        "current": await _present_period(overview.current, currency),
        "previous": await _present_period(overview.previous, currency),
    }


def present_meta(scope: AnalyticsScope, cached: bool) -> dict:
    return present_scope_meta(scope, cached)


async def _present_period(summary: PeriodSummaryDTO, currency: str) -> dict:
    return {
        "since": to_iso(summary.since),
        "until": to_iso(summary.until),
        "inflow": await money_at_scale(summary.inflow, currency),
        "outflow": await money_at_scale(summary.outflow, currency),
        "net": await money_at_scale(summary.net, currency),
        "savings_rate": as_percentage(summary.savings_rate),
        "transactions_count": summary.transactions_count,
        "active_days": summary.active_days,
        "average_daily_outflow": await money_at_scale(summary.average_daily_outflow, currency),
        "largest_expense": await present_optional_transaction_brief(
            summary.largest_expense,
            currency,
        ),
        "largest_income": await present_optional_transaction_brief(
            summary.largest_income,
            currency,
        ),
        "top_expense_category": await _present_top_category(
            summary.top_expense_category,
            currency,
        ),
    }


async def _present_top_category(top_category: TopCategoryDTO | None, currency: str) -> dict | None:
    if top_category is None:
        return None

    return {
        "category": present_analytics_category(top_category.category),
        "amount": await money_at_scale(top_category.amount, currency),
        "share": as_percentage(top_category.share),
    }
