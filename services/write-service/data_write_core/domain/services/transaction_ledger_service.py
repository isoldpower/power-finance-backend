from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ..entities import TransactionEntity


@dataclass(frozen=True)
class CollapsedTransaction:
    """An original transaction with all its later effects already applied."""

    transaction: TransactionEntity
    effective_amount: Decimal


def collapse_ledger(
    transactions: list[TransactionEntity],
) -> list[CollapsedTransaction]:
    """Fold the append-only ledger into the user-facing transactions."""

    cancelled_ids = _find_cancelled_transactions(transactions)
    adjustment_deltas = _find_adjustment_deltas(transactions)

    collapsed_transactions: list[CollapsedTransaction] = []
    for transaction_row in transactions:
        # Effect rows (inverses / adjustments) are never standalone transactions.
        if transaction_row.cancels_other is not None or transaction_row.adjusts_other is not None:
            continue

        # An original that has since been cancelled collapses to nothing.
        original_id = UUID(transaction_row.unique_id)
        if original_id in cancelled_ids:
            continue

        effective_amount = transaction_row.amount + adjustment_deltas.get(original_id, Decimal("0"))
        collapsed_transactions.append(
            CollapsedTransaction(
                transaction=transaction_row,
                effective_amount=effective_amount,
            )
        )

    return collapsed_transactions


def _find_cancelled_transactions(transactions: list[TransactionEntity]) -> set[UUID]:
    return {row.cancels_other for row in transactions if row.cancels_other is not None}


def _find_adjustment_deltas(transactions: list[TransactionEntity]) -> dict[UUID, Decimal]:
    adjustment_deltas: dict[UUID, Decimal] = {}
    for transaction_row in transactions:
        if transaction_row.adjusts_other is not None:
            stored_delta = adjustment_deltas.get(transaction_row.adjusts_other, Decimal("0"))
            adjustment_deltas[transaction_row.adjusts_other] = stored_delta + transaction_row.amount

    return adjustment_deltas
