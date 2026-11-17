from data_read_core.shared.analytics import (
    AnalyticsScope,
    as_percentage,
    present_analytics_category,
    present_scope_meta,
)
from data_read_core.shared.money import money_at_scale

from ..dtos import CategoriesDTO, CategoryShareDTO


async def present_categories(categories: CategoriesDTO, currency: str) -> dict:
    return {
        "type": categories.side.value,
        "total": await money_at_scale(categories.total, currency),
        "categories": [
            await _present_category(category_share, currency)
            for category_share in categories.categories
        ],
    }


def present_meta(scope: AnalyticsScope, cached: bool) -> dict:
    return present_scope_meta(scope, cached)


async def _present_category(category_share: CategoryShareDTO, currency: str) -> dict:
    return {
        "category": present_analytics_category(category_share.category),
        "amount": await money_at_scale(category_share.amount, currency),
        "share": as_percentage(category_share.share),
        "transactions_count": category_share.transactions_count,
        "average": await money_at_scale(category_share.average, currency),
        "previous_amount": await money_at_scale(category_share.previous_amount, currency),
        "change_percentage": as_percentage(category_share.change_percentage),
    }
