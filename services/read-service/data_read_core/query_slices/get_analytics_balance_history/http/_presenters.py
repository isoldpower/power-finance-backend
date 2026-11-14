from data_read_core.shared.analytics import (
    AnalyticsScope,
    present_scope_meta,
    present_wallet_option,
)
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..dtos import BalanceHistoryDTO, WalletBalanceSeriesDTO


async def present_balance_history(balance_history: BalanceHistoryDTO, currency: str) -> dict:
    return {
        "timestamps": [to_iso(timestamp) for timestamp in balance_history.timestamps],
        "total": [await money_at_scale(total, currency) for total in balance_history.totals],
        "wallets": [
            await _present_wallet_series(series, currency) for series in balance_history.wallets
        ],
    }


def present_meta(scope: AnalyticsScope, points: int, cached: bool) -> dict:
    return present_scope_meta(scope, cached, points=points)


async def _present_wallet_series(series: WalletBalanceSeriesDTO, currency: str) -> dict:
    return {
        "wallet": present_wallet_option(series.wallet),
        "balances": [
            await money_at_scale(balance, currency) for balance in series.converted_balances
        ],
        "native_balances": [
            await money_at_scale(balance, series.wallet.currency)
            for balance in series.native_balances
        ],
    }
