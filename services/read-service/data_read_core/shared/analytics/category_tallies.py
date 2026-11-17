from decimal import Decimal
from typing import NamedTuple

from .config import ZERO
from .ledger import AnalyticsLedger
from .ledger_rows import AnalyticsCategory, LedgerRow


class CategoryTally(NamedTuple):
    category: AnalyticsCategory | None
    amount: Decimal
    transactions_count: int


def tally_by_category(ledger: AnalyticsLedger, rows: list[LedgerRow]) -> list[CategoryTally]:
    amounts_by_category: dict[AnalyticsCategory | None, Decimal] = {}
    counts_by_category: dict[AnalyticsCategory | None, int] = {}
    for row in rows:
        amounts_by_category[row.category] = amounts_by_category.get(
            row.category, ZERO
        ) + ledger.converted_magnitude(row)
        counts_by_category[row.category] = counts_by_category.get(row.category, 0) + 1

    return sorted(
        (
            CategoryTally(
                category=category,
                amount=amount,
                transactions_count=counts_by_category[category],
            )
            for category, amount in amounts_by_category.items()
        ),
        key=lambda tally: tally.amount,
        reverse=True,
    )
