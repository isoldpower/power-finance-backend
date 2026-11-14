from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    change_between,
    share_of,
    tally_by_category,
)

from .config import REPORT_NAME
from .dtos import CategoriesDTO, CategoryShareDTO, GetAnalyticsCategoriesQuery


class GetAnalyticsCategoriesQueryHandler(AnalyticsReportHandler[GetAnalyticsCategoriesQuery]):
    report_name = REPORT_NAME
    report_type = CategoriesDTO

    async def _build(self, query: GetAnalyticsCategoriesQuery) -> CategoriesDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        current_tallies = tally_by_category(
            ledger,
            await ledger.fetch_flows(query.scope.window, side=query.side),
        )
        previous_amounts = {
            tally.category: tally.amount
            for tally in tally_by_category(
                ledger,
                await ledger.fetch_flows(query.scope.window.previous, side=query.side),
            )
        }
        total = sum((tally.amount for tally in current_tallies), ZERO)

        return CategoriesDTO(
            side=query.side,
            total=total,
            categories=[
                CategoryShareDTO(
                    category=tally.category,
                    amount=tally.amount,
                    share=share_of(tally.amount, total),
                    transactions_count=tally.transactions_count,
                    previous_amount=previous_amounts.get(tally.category, ZERO),
                    change_percentage=change_between(
                        tally.amount,
                        previous_amounts.get(tally.category, ZERO),
                    ),
                )
                for tally in current_tallies
            ],
        )
