import asyncio
from dataclasses import dataclass
from uuid import UUID

from finances.domain.builders import WalletBuilder

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_dto, wallet_to_dto
from ...dtos import TransactionDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: UUID
    user_id: int


class DeleteTransactionCommandHandler(UseCaseEvently):
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ):
        super().__init__()
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    @atomic_evently_command()
    async def handle(self, command: DeleteTransactionCommand) -> TransactionDTO:
        inverse_transaction = await self.transaction_repository.delete_transaction_by_id(
            user_id=command.user_id,
            transaction_id=command.transaction_id,
        )
        inverse_transaction.migrate_event_collector(self.event_collector)

        wallet, checkpoint = await asyncio.gather(
            self.wallet_repository.get_user_wallet_by_id(
                wallet_id=inverse_transaction.source_wallet_id,
                user_id=command.user_id,
            ),
            self.transaction_repository.get_checkpoint(inverse_transaction.source_wallet_id),
        )
        wallet = (
            WalletBuilder(wallet)
                .set_checkpoint(checkpoint)
                .set_transactions(await self.transaction_repository.get_unsettled_transactions(
                    inverse_transaction.source_wallet_id, checkpoint.settled_at if checkpoint else None
                ))
                .build_wallet()
        )

        return transaction_to_dto(inverse_transaction, wallet_to_dto(wallet))
