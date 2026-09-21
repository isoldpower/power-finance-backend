from uuid import UUID

from data_write_core.domain.entities import BalanceCheckpointEntity, MoneyFlowEntity, WalletEntity

from ..interfaces import MoneyFlowRepository


async def load_balance_inputs(
    wallet: WalletEntity,
    money_flow_repository: MoneyFlowRepository,
) -> tuple[BalanceCheckpointEntity | None, list[MoneyFlowEntity]]:
    wallet_id = UUID(wallet.unique_id)
    checkpoint = await money_flow_repository.get_checkpoint(wallet_id)
    settled_at = checkpoint.created_at.isoformat() if checkpoint else None
    unsettled_transactions = await money_flow_repository.get_unsettled_flows(
        wallet_id,
        settled_at,
    )

    return checkpoint, unsettled_transactions
