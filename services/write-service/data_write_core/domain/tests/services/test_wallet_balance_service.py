from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    TransactionEntity,
    WalletEntity,
)
from data_write_core.domain.services import reconstruct_balance
from data_write_core.domain.value_objects import TransactionData, WalletData

WALLET = "11111111-1111-1111-1111-111111111111"


def _wallet() -> WalletEntity:
    moment = datetime(2026, 1, 1)
    return WalletEntity.create(
        data=WalletData(title="Main", currency_code="USD"),
        id=WALLET,
        user_id="7",
        created_at=moment,
        updated_at=moment,
    )


def _tx(amount: str) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        user_id=7,
        created_at=datetime(2026, 1, 2),
        data=TransactionData(
            source_wallet_id=UUID(WALLET),
            amount=Decimal(amount),
            cancels_other=None,
            adjusts_other=None,
        ),
    )


def test_folds_unsettled_onto_checkpoint():
    checkpoint = BalanceCheckpointEntity(
        id=WALLET, created_at=datetime(2026, 1, 1), balance=Decimal("100")
    )

    balance = reconstruct_balance(_wallet(), checkpoint, [_tx("50"), _tx("-20")])

    assert balance == Decimal("130")


def test_no_checkpoint_starts_from_zero():
    assert reconstruct_balance(_wallet(), None, [_tx("42")]) == Decimal("42")


def test_no_activity_is_zero():
    assert reconstruct_balance(_wallet(), None, []) == Decimal("0")
