from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity
from data_write_core.infrastructure.outbox_saga import (
    ImmudbTransactionStep,
    PostgresOutboxEmissionStep,
    SagaCoordinator,
    TransactionDeletedOutboxEvent,
)

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, transaction_to_dto
from ..interfaces import OutboxRepository, TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._loader_mixins import LoadTransactionMixin, LoadWalletMixin


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: UUID
    user_id: int


class DeleteTransactionCommandHandler(
    CommandHandlerBase[TransactionDTO], LoadWalletMixin, LoadTransactionMixin
):
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
        transaction_repository = transaction_repository or registry.transaction_repository
        wallet_repository = wallet_repository or registry.wallet_repository
        outbox_repository = outbox_repository or registry.outbox_repository

        LoadWalletMixin.__init__(self, wallet_repository, transaction_repository)
        LoadTransactionMixin.__init__(self, transaction_repository)

        self._transaction_repository = transaction_repository
        self._wallet_repository = wallet_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: DeleteTransactionCommand) -> tuple[TransactionDTO, int]:
        transaction_aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )
        inverse_transaction, latest_sequence = await self._run_transactions_saga(
            transaction_aggregate,
        )
        wallet_dto = await self.load_wallet_dto(
            wallet_id=transaction_aggregate.root.source_wallet_id,
            user_id=command.user_id,
        )
        transaction_dto = transaction_to_dto(inverse_transaction, wallet_dto)

        await self._publish_domain_events(transaction_aggregate)
        return transaction_dto, latest_sequence

    async def _run_transactions_saga(
        self,
        transaction_aggregate: TransactionAggregate,
    ) -> tuple[TransactionEntity, int]:
        inverse_transaction = transaction_aggregate.delete_self()

        saga_coordinator = SagaCoordinator(
            transaction_steps=[
                ImmudbTransactionStep(
                    self._transaction_repository,
                    inverse_transaction,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                events=[
                    TransactionDeletedOutboxEvent(
                        transaction_id=UUID(transaction_aggregate.unique_id),
                        wallet_id=transaction_aggregate.root.source_wallet_id,
                        user_id=int(transaction_aggregate.root.user_id),
                        amount=transaction_aggregate.root.amount,
                        cancelled_by=UUID(inverse_transaction.unique_id),
                        created_at=inverse_transaction.created_at,
                    )
                ],
            ),
        )
        latest_sequence = await saga_coordinator.run_transaction()

        return inverse_transaction, latest_sequence
