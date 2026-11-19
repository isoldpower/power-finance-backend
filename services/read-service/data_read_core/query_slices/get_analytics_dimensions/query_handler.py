from data_read_core.shared.analytics import (
    AnalyticsReportHandler,
    LedgerSide,
    fetch_category_vocabulary,
    fetch_open_wallets,
    fetch_transaction_time_bounds,
)

from .config import REPORT_NAME
from .dtos import DimensionsDTO, GetAnalyticsDimensionsQuery


class GetAnalyticsDimensionsQueryHandler(AnalyticsReportHandler[GetAnalyticsDimensionsQuery]):
    report_name = REPORT_NAME
    report_type = DimensionsDTO

    async def _build(self, query: GetAnalyticsDimensionsQuery) -> DimensionsDTO:
        open_wallets = await fetch_open_wallets(query.user_id)
        wallet_identifiers = [wallet.identifier for wallet in open_wallets]
        category_vocabulary = await fetch_category_vocabulary(query.user_id, wallet_identifiers)
        time_bounds = await fetch_transaction_time_bounds(query.user_id, wallet_identifiers)

        return DimensionsDTO(
            wallets=open_wallets,
            expense_categories=category_vocabulary[LedgerSide.EXPENSE],
            income_categories=category_vocabulary[LedgerSide.INCOME],
            first_transaction_at=time_bounds.first_transaction_at,
            last_transaction_at=time_bounds.last_transaction_at,
        )
