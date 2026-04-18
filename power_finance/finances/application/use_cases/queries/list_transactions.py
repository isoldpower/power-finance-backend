import asyncio
import logging
from dataclasses import dataclass

from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_plain_dto, wallet_to_dto
from ...dtos import TransactionPlainDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class ListTransactionsQuery:
    user_id: int


logger = logging.getLogger(__name__)


class ListTransactionsQueryHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    async def handle(self, query: ListTransactionsQuery) -> list[TransactionPlainDTO]:
        logger.info("ListTransactionsQueryHandler: Handling ListTransactionsQuery for User ID: %s", query.user_id)
        user_transactions = await self.transaction_repository.get_user_transactions(query.user_id)

        wallets = await asyncio.gather(*[
            self.wallet_repository.get_user_wallet_by_id(
                wallet_id=transaction.source_wallet_id,
                user_id=query.user_id,
            ) for transaction in user_transactions
        ])
        wallet_transactions = await asyncio.gather(*[
            self.transaction_repository.get_wallet_transactions(wallet.id)
            for wallet in wallets
        ])
        for wallet, transactions in zip(wallets, wallet_transactions):
            wallet.transactions = transactions

        logger.info("ListTransactionsQueryHandler: Successfully retrieved %d transactions for User ID: %s", len(user_transactions), query.user_id)
        return [
            transaction_to_plain_dto(transaction, wallet_to_dto(wallets[i]))
            for i, transaction in enumerate(user_transactions)
        ]
