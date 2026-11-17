from data_read_core.shared.analytics import (
    AnalyticsLedger,
    AnalyticsReportHandler,
    LedgerRow,
    LedgerSide,
    brief_of,
    normalised_counterparty_name,
)

from .config import REPORT_NAME, TransactionOrder
from .dtos import AnalyticsTransactionsDTO, ListAnalyticsTransactionsQuery


class ListAnalyticsTransactionsQueryHandler(AnalyticsReportHandler[ListAnalyticsTransactionsQuery]):
    report_name = REPORT_NAME
    report_type = AnalyticsTransactionsDTO

    async def _build(self, query: ListAnalyticsTransactionsQuery) -> AnalyticsTransactionsDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        rows = [
            row
            for row in await ledger.fetch_flows(query.scope.window, side=query.side)
            if _matches_counterparty(row, query.counterparty_name)
        ]

        return AnalyticsTransactionsDTO(
            transactions=[
                brief_of(row, ledger) for row in _ordered(ledger, rows, query.order)[: query.limit]
            ],
            total=len(rows),
            total_inflow=ledger.converted_total(rows, LedgerSide.INCOME),
            total_outflow=ledger.converted_total(rows, LedgerSide.EXPENSE),
        )


def _matches_counterparty(row: LedgerRow, counterparty_name: str | None) -> bool:
    if counterparty_name is None:
        return True

    return normalised_counterparty_name(row.name) == normalised_counterparty_name(counterparty_name)


def _ordered(
    ledger: AnalyticsLedger,
    rows: list[LedgerRow],
    order: TransactionOrder,
) -> list[LedgerRow]:
    newest_first = sorted(rows, key=lambda row: (row.created_at, row.identifier), reverse=True)
    if order is TransactionOrder.CREATED_DESCENDING:
        return newest_first

    return sorted(newest_first, key=ledger.converted_magnitude, reverse=True)
