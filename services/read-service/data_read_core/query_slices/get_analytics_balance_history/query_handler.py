from decimal import Decimal

from data_read_core.shared.analytics import (
    AnalyticsLedger,
    AnalyticsReportHandler,
    native_balance_series,
)
from data_read_core.shared.money import CURRENCY_CATALOG

from .config import REPORT_NAME
from .dtos import BalanceHistoryDTO, GetAnalyticsBalanceHistoryQuery, WalletBalanceSeriesDTO


class GetAnalyticsBalanceHistoryQueryHandler(
    AnalyticsReportHandler[GetAnalyticsBalanceHistoryQuery]
):
    report_name = REPORT_NAME
    report_type = BalanceHistoryDTO

    async def _build(self, query: GetAnalyticsBalanceHistoryQuery) -> BalanceHistoryDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        sample_instants = query.sample_instants
        native_balances_by_wallet = await native_balance_series(
            ledger,
            sample_instants,
            include_instant=True,
        )
        target_quantum = Decimal(1).scaleb(
            -await CURRENCY_CATALOG.decimals_or_default(query.scope.currency)
        )

        return BalanceHistoryDTO(
            timestamps=sample_instants,
            wallets=[
                WalletBalanceSeriesDTO(
                    wallet=wallet,
                    converted_balances=[
                        ledger.converted_balance(native_balance, wallet).quantize(target_quantum)
                        for native_balance in native_balances_by_wallet[wallet.identifier]
                    ],
                    native_balances=native_balances_by_wallet[wallet.identifier],
                )
                for wallet in ledger.selected_wallets
            ],
        )
