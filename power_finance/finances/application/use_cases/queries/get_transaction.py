import asyncio
from dataclasses import dataclass
from uuid import UUID

from finances.domain.entities import TransactionParticipant
from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class GetTransactionQuery:
    user_id: int
    transaction_id: str


class GetTransactionQueryHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None
    ):
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    async def _load_wallets(
            self,
            user_id: int,
            sender: TransactionParticipant,
            receiver: TransactionParticipant,
    ):
        return await asyncio.gather(*[
            (self.wallet_repository.get_user_wallet_by_id(
                sender.wallet_id,
                user_id,
            ) if sender else None),
            (self.wallet_repository.get_user_wallet_by_id(
                receiver.wallet_id,
                user_id,
            ) if receiver else None)
        ])

    async def handle(self, query: GetTransactionQuery) -> TransactionDTO:
        requested_transaction = await self.transaction_repository.get_user_transaction_by_id(
            query.user_id,
            UUID(query.transaction_id)
        )
        sender_wallet, receiver_wallet = await self._load_wallets(
            query.user_id,
            requested_transaction.sender,
            requested_transaction.receiver
        )

        return transaction_to_dto(
            requested_transaction,
            sender_wallet,
            receiver_wallet
        )