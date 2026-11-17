from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    LedgerRow,
    normalised_counterparty_name,
    share_of,
)

from .config import REPORT_NAME
from .dtos import CounterpartiesDTO, CounterpartyDTO, ListAnalyticsCounterpartiesQuery


@dataclass
class CounterpartyTally:
    last_seen_at: datetime
    spelling_counts: Counter = field(default_factory=Counter)
    category_counts: Counter = field(default_factory=Counter)
    amount: Decimal = ZERO
    transactions_count: int = 0

    def add(self, row: LedgerRow, converted_amount: Decimal) -> None:
        self.spelling_counts[row.name.strip()] += 1
        self.category_counts[row.category] += 1
        self.amount += converted_amount
        self.transactions_count += 1
        self.last_seen_at = max(self.last_seen_at, row.created_at)


class ListAnalyticsCounterpartiesQueryHandler(
    AnalyticsReportHandler[ListAnalyticsCounterpartiesQuery]
):
    report_name = REPORT_NAME
    report_type = CounterpartiesDTO

    async def _build(self, query: ListAnalyticsCounterpartiesQuery) -> CounterpartiesDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        rows = await ledger.fetch_flows(query.scope.window, side=query.side)
        tallies_by_name: dict[str, CounterpartyTally] = {}
        side_total = ZERO

        for row in rows:
            converted_amount = ledger.converted_magnitude(row)
            side_total += converted_amount
            tallies_by_name.setdefault(
                normalised_counterparty_name(row.name),
                CounterpartyTally(last_seen_at=row.created_at),
            ).add(row, converted_amount)

        ranked_tallies = sorted(
            tallies_by_name.values(),
            key=lambda tally: tally.amount,
            reverse=True,
        )

        return CounterpartiesDTO(
            counterparties=[
                CounterpartyDTO(
                    name=tally.spelling_counts.most_common(1)[0][0],
                    category=tally.category_counts.most_common(1)[0][0],
                    amount=tally.amount,
                    share=share_of(tally.amount, side_total),
                    transactions_count=tally.transactions_count,
                    last_seen_at=tally.last_seen_at,
                )
                for tally in ranked_tallies[: query.limit]
            ],
            total_counterparties=len(ranked_tallies),
        )
