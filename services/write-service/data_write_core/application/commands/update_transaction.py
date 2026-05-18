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


class UpdateTransactionCommandHandler(CommandHandlerBase, LoadWalletMixin, LoadTransactionMixin):
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

    async def handle(self, command: UpdateTransactionCommand) -> TransactionDTO:
        transaction_aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )

        adjustment_transaction = transaction_aggregate.adjust_self(new_amount=command.new_amount)
        if adjustment_transaction is not transaction_aggregate.root:
            await self._run_transactions_sage(adjustment_transaction)

        wallet_dto = await self.load_wallet_dto(
            wallet_id=transaction_aggregate.root.source_wallet_id,
            user_id=command.user_id,
        )

        await self._publish_domain_events(transaction_aggregate)
        return transaction_to_dto(adjustment_transaction, wallet_dto)

    async def _run_transactions_sage(self, adjustment_transaction: TransactionEntity) -> None:
        saga = SagaCoordinator(
            transaction_steps=[
                ImmudbTransactionStep(self._transaction_repository, adjustment_transaction),
            ],
            final_step=OutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                events=[
                    TransactionCreatedOutboxEvent(
                        transaction_id=UUID(adjustment_transaction.unique_id),
                        wallet_id=adjustment_transaction.source_wallet_id,
                        user_id=int(adjustment_transaction.user_id),
                        amount=adjustment_transaction.amount,
                        created_at=adjustment_transaction.created_at,
                    )
                ],
            ),
        )

        await saga.run_transaction()
