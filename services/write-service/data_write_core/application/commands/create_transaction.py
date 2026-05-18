from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import TransactionEntity
from data_write_core.infrastructure.outbox_saga import (
    ImmudbTransactionStep,
    OutboxEmissionStep,
    SagaCoordinator,
    TransactionCreatedOutboxEvent,
)

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, transaction_to_dto, wallet_to_dto
from ..interfaces import OutboxRepository, TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._loader_mixins import LoadWalletMixin


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    source_wallet_id: UUID
    amount: Decimal


class CreateTransactionCommandHandler(CommandHandlerBase, LoadWalletMixin):
    _transaction_repository: TransactionRepository
    _wallet_repository: WalletRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        wallet_repository = wallet_repository or registry.wallet_repository
        transaction_repository = transaction_repository or registry.transaction_repository
        outbox_repository = outbox_repository or registry.outbox_repository

        LoadWalletMixin.__init__(self, wallet_repository, transaction_repository)

        self._transaction_repository = transaction_repository
        self._wallet_repository = wallet_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: CreateTransactionCommand) -> TransactionDTO:
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.source_wallet_id,
            user_id=command.user_id,
        )
        new_transaction = wallet_aggregate.apply_transaction(
            amount=command.amount,
        )

        await self._write_with_saga(new_transaction)
        await self._publish_domain_events(wallet_aggregate)

        return transaction_to_dto(
            new_transaction,
            wallet_to_dto(
                wallet_aggregate.root,
                balance_amount=wallet_aggregate.balance,
            ),
        )

    async def _write_with_saga(self, new_transaction: TransactionEntity):
        outbox_events = [
            TransactionCreatedOutboxEvent(
                transaction_id=UUID(new_transaction.unique_id),
                wallet_id=new_transaction.source_wallet_id,
                user_id=int(new_transaction.user_id),
                amount=new_transaction.amount,
                created_at=new_transaction.created_at,
            )
        ]

        saga = SagaCoordinator(
            transaction_steps=[
                ImmudbTransactionStep(
                    repository=self._transaction_repository,
                    transaction=new_transaction,
                ),
            ],
            final_step=OutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                events=outbox_events,
            ),
        )

        await saga.run_transaction()
