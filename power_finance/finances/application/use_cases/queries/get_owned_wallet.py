import asyncio
from dataclasses import dataclass
from uuid import UUID

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, TransactionRepository


@dataclass
class GetOwnedWalletQuery:
    user_id: int
    wallet_id: str


class GetOwnedWalletQueryHandler:
    wallet_repository: WalletRepository
    transaction_repository: TransactionRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ):
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository
        self.transaction_repository = transaction_repository or registry.transaction_repository

    async def handle(self, query: GetOwnedWalletQuery) -> WalletDTO:
        wallet_id = UUID(query.wallet_id)
        wallet, transactions = await asyncio.gather(*[
            self.wallet_repository.get_user_wallet_by_id(wallet_id, query.user_id),
            self.transaction_repository.get_wallet_transactions(wallet_id),
        ])
        wallet.transactions = transactions

        return wallet_to_dto(wallet)