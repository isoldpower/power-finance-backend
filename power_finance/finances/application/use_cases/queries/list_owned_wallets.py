import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, TransactionRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ListOwnedWalletsQuery:
    user_id: int
    limit: Optional[int]
    offset: Optional[int]

class ListOwnedWalletsQueryHandler:
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

    async def handle(self, query: ListOwnedWalletsQuery) -> list[WalletDTO]:
        logger.info(
            "ListOwnedWalletsQueryHandler: Handling ListOwnedWalletsQuery for User ID: %s",
            query.user_id
        )
        user_wallets = await self.wallet_repository.get_user_wallets(query.user_id)
        wallet_transactions = await asyncio.gather(*[
            self.transaction_repository.get_wallet_transactions(wallet.id)
            for wallet in user_wallets
        ])
        for wallet, transactions in zip(user_wallets, wallet_transactions):
            wallet.transactions = transactions

        logger.info(
            "ListOwnedWalletsQueryHandler: Successfully retrieved %d wallets for User ID: %s",
            len(user_wallets), query.user_id
        )
        return [wallet_to_dto(wallet) for wallet in user_wallets]