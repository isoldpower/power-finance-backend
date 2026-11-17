from datetime import UTC, datetime

from data_read_core.shared.analytics import present_analytics_category, present_wallet_option
from data_read_core.shared.timestamps import to_iso

from ..dtos import DimensionsDTO


def present_dimensions(dimensions: DimensionsDTO) -> dict:
    return {
        "wallets": [present_wallet_option(wallet) for wallet in dimensions.wallets],
        "categories": {
            "expense": [
                present_analytics_category(category) for category in dimensions.expense_categories
            ],
            "income": [
                present_analytics_category(category) for category in dimensions.income_categories
            ],
        },
        "first_transaction_at": to_iso(dimensions.first_transaction_at),
        "last_transaction_at": to_iso(dimensions.last_transaction_at),
    }


def present_meta(currency: str, cached: bool) -> dict:
    return {
        "currency": currency,
        "generated_at": to_iso(datetime.now(UTC)),
        "cached": cached,
    }
