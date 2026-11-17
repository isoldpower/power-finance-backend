from data_read_core.shared.analytics import (
    AnalyticsLedger,
    AnalyticsReportHandler,
    LedgerSide,
)
from data_read_core.shared.money import smallest_unit_of

from .config import REPORT_NAME
from .dtos import GetAnalyticsMoneyFlowQuery, MoneyFlowDTO
from .flow_graph import MoneyFlowGraph


class GetAnalyticsMoneyFlowQueryHandler(AnalyticsReportHandler[GetAnalyticsMoneyFlowQuery]):
    report_name = REPORT_NAME
    report_type = MoneyFlowDTO

    async def _build(self, query: GetAnalyticsMoneyFlowQuery) -> MoneyFlowDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        rows = await ledger.fetch_flows(query.scope.window, apply_categories=False)
        flow_graph = MoneyFlowGraph(ledger, await smallest_unit_of(query.scope.currency))

        for wallet in ledger.selected_wallets:
            flow_graph.add_wallet(
                wallet,
                [row for row in rows if row.wallet_identifier == wallet.identifier],
            )

        return MoneyFlowDTO(
            nodes=flow_graph.nodes,
            links=flow_graph.links,
            inflow=ledger.converted_total(rows, LedgerSide.INCOME),
            outflow=ledger.converted_total(rows, LedgerSide.EXPENSE),
        )
