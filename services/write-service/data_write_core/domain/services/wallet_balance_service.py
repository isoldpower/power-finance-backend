from decimal import Decimal

from ..aggregates import WalletAggregate
from ..entities import BalanceCheckpointEntity, TransactionEntity, WalletEntity


def reconstruct_balance(
    wallet: WalletEntity,
    checkpoint: BalanceCheckpointEntity | None,
    unsettled_transactions: list[TransactionEntity],
) -> Decimal:
    """Fold the unsettled tail of the ledger onto the latest balance checkpoint."""

    return WalletAggregate(
        wallet_entity=wallet,
        unsettled_transactions=unsettled_transactions,
        balance_checkpoint=checkpoint,
    ).balance
