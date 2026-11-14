from decimal import Decimal
from typing import NamedTuple

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    BucketLocator,
    LedgerSide,
    native_balance_series,
)

from .config import REPORT_NAME
from .dtos import CashFlowBucketDTO, CashFlowDTO, GetAnalyticsCashFlowQuery


class BucketTally(NamedTuple):
    inflow: Decimal
    outflow: Decimal
    transactions_count: int


EMPTY_TALLY = BucketTally(inflow=ZERO, outflow=ZERO, transactions_count=0)


class GetAnalyticsCashFlowQueryHandler(AnalyticsReportHandler[GetAnalyticsCashFlowQuery]):
    report_name = REPORT_NAME
    report_type = CashFlowDTO

    async def _build(self, query: GetAnalyticsCashFlowQuery) -> CashFlowDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        tallies = await _tally_buckets(ledger, query)
        closing_balances = await _closing_balances(ledger, query)

        return CashFlowDTO(
            buckets=[
                CashFlowBucketDTO(
                    start=bucket.start,
                    end=bucket.end,
                    inflow=tally.inflow,
                    outflow=tally.outflow,
                    transactions_count=tally.transactions_count,
                    closing_balance=closing_balance,
                )
                for bucket, tally, closing_balance in zip(
                    query.buckets,
                    tallies,
                    closing_balances,
                    strict=True,
                )
            ]
        )


async def _tally_buckets(
    ledger: AnalyticsLedger,
    query: GetAnalyticsCashFlowQuery,
) -> list[BucketTally]:
    bucket_locator = BucketLocator(query.buckets)
    tallies = [EMPTY_TALLY] * len(query.buckets)

    for row in await ledger.fetch_flows(query.scope.window):
        bucket_index = bucket_locator.index_of(row.created_at)
        if bucket_index is None:
            continue

        converted_amount = ledger.converted_magnitude(row)
        current_tally = tallies[bucket_index]
        tallies[bucket_index] = BucketTally(
            inflow=current_tally.inflow
            + (converted_amount if row.side is LedgerSide.INCOME else ZERO),
            outflow=current_tally.outflow
            + (converted_amount if row.side is LedgerSide.EXPENSE else ZERO),
            transactions_count=current_tally.transactions_count + 1,
        )

    return tallies


async def _closing_balances(
    ledger: AnalyticsLedger,
    query: GetAnalyticsCashFlowQuery,
) -> list[Decimal]:
    native_balances_by_wallet = await native_balance_series(
        ledger,
        [bucket.end for bucket in query.buckets],
        include_instant=False,
    )
    closing_balances = [ZERO] * len(query.buckets)
    for wallet in ledger.selected_wallets:
        for bucket_index, native_balance in enumerate(native_balances_by_wallet[wallet.identifier]):
            closing_balances[bucket_index] += ledger.converted_balance(native_balance, wallet)

    return closing_balances
