from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.services import CollapsedTransaction, collapse_ledger
from data_write_core.domain.value_objects import TransactionData

WALLET = "11111111-1111-1111-1111-111111111111"
TX_ORIGINAL = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TX_EFFECT = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _tx(
    transaction_id: str,
    amount: str,
    *,
    created_at: datetime | None = None,
    cancels_other: UUID | None = None,
    adjusts_other: UUID | None = None,
) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=UUID(transaction_id),
        user_id=7,
        created_at=created_at or datetime(2026, 1, 1),
        data=TransactionData(
            source_wallet_id=UUID(WALLET),
            amount=Decimal(amount),
            cancels_other=cancels_other,
            adjusts_other=adjusts_other,
        ),
    )


def test_plain_transactions_pass_through_unchanged():
    transactions = [_tx(TX_ORIGINAL, "20")]

    collapsed = collapse_ledger(transactions)

    assert collapsed == [
        CollapsedTransaction(transaction=transactions[0], effective_amount=Decimal("20"))
    ]


def test_cancelled_original_and_its_inverse_collapse_to_nothing():
    original = _tx(TX_ORIGINAL, "20")
    inverse = _tx(TX_EFFECT, "-20", cancels_other=UUID(TX_ORIGINAL))

    assert collapse_ledger([original, inverse]) == []


def test_adjustment_delta_folds_into_original():
    original = _tx(TX_ORIGINAL, "20")
    adjustment = _tx(TX_EFFECT, "5", adjusts_other=UUID(TX_ORIGINAL))

    collapsed = collapse_ledger([original, adjustment])

    assert len(collapsed) == 1
    assert collapsed[0].transaction is original
    assert collapsed[0].effective_amount == Decimal("25")


def test_effect_rows_are_never_emitted_on_their_own():
    inverse = _tx(TX_EFFECT, "-20", cancels_other=UUID(TX_ORIGINAL))

    assert collapse_ledger([inverse]) == []
