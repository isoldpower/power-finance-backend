from decimal import Decimal

from ..aggregates import WalletAggregate
from ..entities import BalanceCheckpointEntity, MoneyFlowEntity, WalletEntity


def reconstruct_balance(
    wallet: WalletEntity,
    checkpoint: BalanceCheckpointEntity | None,
    unsettled_transactions: list[MoneyFlowEntity],
) -> Decimal:
    return WalletAggregate(
        wallet_entity=wallet,
        unsettled_transactions=unsettled_transactions,
        balance_checkpoint=checkpoint,
    ).balance
