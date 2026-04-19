import asyncio
from dataclasses import dataclass
from uuid import UUID

from finances.domain.builders import WalletBuilder

from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto, wallet_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class GetTransactionQuery:
    user_id: int
    transaction_id: UUID


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

    async def handle(self, query: GetTransactionQuery) -> TransactionDTO:
        requested_transaction = await self.transaction_repository.get_user_transaction_by_id(
            user_id=query.user_id,
            transaction_id=query.transaction_id,
        )
        wallet_id = requested_transaction.source_wallet_id
        wallet, checkpoint = await asyncio.gather(
            self.wallet_repository.get_user_wallet_by_id(
                wallet_id=wallet_id,
                user_id=query.user_id,
            ),
            self.transaction_repository.get_checkpoint(wallet_id),
        )
        wallet = (
            WalletBuilder(wallet)
                .set_checkpoint(checkpoint)
                .set_transactions(await self.transaction_repository.get_unsettled_transactions(
                    wallet_id, checkpoint.settled_at if checkpoint else None
                ))
                .build_wallet()
        )
        return transaction_to_dto(
            transaction=requested_transaction,
            source_wallet=wallet_to_dto(wallet),
        )
