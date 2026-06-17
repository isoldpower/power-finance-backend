import asyncio
from dataclasses import dataclass

from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.services import reconstruct_balance

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import TransactionRepository, WalletRepository
from ._wallet_balance import load_balance_inputs


@dataclass(frozen=True)
class ListFallbackWalletsQuery:
    user_id: int
    limit: int
    offset: int


class ListFallbackWalletsQueryHandler:
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

    async def handle(self, query: ListFallbackWalletsQuery) -> tuple[list[WalletDTO], int]:
        wallets = await self._wallet_repository.get_user_wallets(
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset,
        )
        total = await self._wallet_repository.count_user_wallets(query.user_id)

        wallet_dtos = await asyncio.gather(*(self._load_wallet_dto(wallet) for wallet in wallets))

        return list(wallet_dtos), total

    async def _load_wallet_dto(self, wallet: WalletEntity) -> WalletDTO:
        checkpoint, unsettled = await load_balance_inputs(wallet, self._transaction_repository)
        balance = reconstruct_balance(wallet, checkpoint, unsettled)

        return wallet_to_dto(wallet, balance_amount=balance)
