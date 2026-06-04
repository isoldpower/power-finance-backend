from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.services import reconstruct_balance

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import TransactionRepository, WalletRepository
from ._wallet_balance import load_balance_inputs


@dataclass(frozen=True)
class GetFallbackWalletQuery:
    user_id: int
    wallet_id: UUID


class GetFallbackWalletQueryHandler:
    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ) -> None:
        if wallet_repository is None or transaction_repository is None:
            registry = get_repository_registry()
            wallet_repository = wallet_repository or registry.wallet_repository
            transaction_repository = transaction_repository or registry.transaction_repository

        self._wallet_repository = wallet_repository
        self._transaction_repository = transaction_repository

    async def handle(self, query: GetFallbackWalletQuery) -> WalletDTO:
        wallet = await self._wallet_repository.get_user_wallet_by_id(
            wallet_id=query.wallet_id,
            user_id=query.user_id,
        )

        checkpoint, unsettled = await load_balance_inputs(wallet, self._transaction_repository)
        balance = reconstruct_balance(wallet, checkpoint, unsettled)

        return wallet_to_dto(wallet, balance_amount=balance)
