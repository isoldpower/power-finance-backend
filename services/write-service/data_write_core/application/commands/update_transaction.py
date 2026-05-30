from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from kafka_messages import TransactionCreated

from data_write_core.domain.entities import TransactionEntity
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    ImmudbTransactionStep,
    PostgresOutboxEmissionStep,
)

from ..bootstrap import get_repository_registry
from ..dtos import TransactionDTO, transaction_to_dto
from ..interfaces import OutboxRepository, TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._loader_mixins import LoadTransactionMixin, LoadWalletMixin


@dataclass(frozen=True)
class UpdateTransactionCommand:
    """Adjusts the amount of an existing transaction by appending an
    immutable adjustment transaction; the original is preserved."""

    user_id: int
    transaction_id: UUID
    new_amount: Decimal


class UpdateTransactionCommandHandler(
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

    async def handle(self, command: UpdateTransactionCommand) -> tuple[TransactionDTO, int]:
        transaction_aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )

        adjustment_transaction = transaction_aggregate.adjust_self(new_amount=command.new_amount)
        if adjustment_transaction is not transaction_aggregate.root:
            latest_sequence = await self._run_transactions_saga(adjustment_transaction)
        else:
            latest_sequence = await self._outbox_repository.get_latest_sequence()

        wallet_dto = await self.load_wallet_dto(
            wallet_id=transaction_aggregate.root.source_wallet_id,
            user_id=command.user_id,
        )
        transaction_dto = transaction_to_dto(adjustment_transaction, wallet_dto)

        await self._publish_domain_events(transaction_aggregate)
        return transaction_dto, latest_sequence

    async def _run_transactions_saga(self, adjustment_transaction: TransactionEntity) -> int:
        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                ImmudbTransactionStep(self._transaction_repository, adjustment_transaction),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        TransactionCreated(
                            transaction_id=adjustment_transaction.unique_id,
                            wallet_id=str(adjustment_transaction.source_wallet_id),
                            user_id=int(adjustment_transaction.user_id),
                            amount=str(adjustment_transaction.amount),
                            created_at=datetime_to_timestamp(adjustment_transaction.created_at),
                        ),
                        aggregate_type="transaction",
                        aggregate_id=adjustment_transaction.unique_id,
                    )
                ],
            ),
        )

        return await saga_coordinator.run_transaction()
