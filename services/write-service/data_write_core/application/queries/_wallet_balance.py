from uuid import UUID

from data_write_core.domain.entities import BalanceCheckpointEntity, TransactionEntity, WalletEntity

from ..interfaces import TransactionRepository


async def load_balance_inputs(
    wallet: WalletEntity,
    transaction_repository: TransactionRepository,
) -> tuple[BalanceCheckpointEntity | None, list[TransactionEntity]]:
    """Fetch the ledger inputs the balance rule needs from the repository port.

    Pure data access: the latest checkpoint plus the unsettled tail recorded
    after it. The fold itself lives in the domain (`reconstruct_balance`).
    """

    wallet_id = UUID(wallet.unique_id)
    checkpoint = await transaction_repository.get_checkpoint(wallet_id)
    settled_at = checkpoint.created_at.isoformat() if checkpoint else None
    unsettled_transactions = await transaction_repository.get_unsettled_transactions(
        wallet_id,
        settled_at,
    )

    return checkpoint, unsettled_transactions
