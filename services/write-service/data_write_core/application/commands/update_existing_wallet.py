from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import WalletUpdated

from data_write_core.domain.aggregates import WalletAggregate
from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.value_objects import WalletData
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import OutboxRepository, TransactionRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._loader_mixins import LoadWalletMixin


@dataclass(frozen=True)
class UpdateExistingWalletCommand:
    """Renames a wallet and changes other metadata. Balance/currency are derived from the immutable
    transaction history and cannot be patched here."""

    user_id: int
    user_external_id: str
    wallet_id: UUID
    new_name: str


class UpdateExistingWalletCommandHandler(CommandHandlerBase[WalletDTO], LoadWalletMixin):
    _wallet_repository: WalletRepository
    _transaction_repository: TransactionRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if wallet_repository is None or transaction_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            wallet_repository = wallet_repository or registry.wallet_repository
            transaction_repository = transaction_repository or registry.transaction_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        LoadWalletMixin.__init__(self, wallet_repository, transaction_repository)

        self._wallet_repository = wallet_repository
        self._transaction_repository = transaction_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: UpdateExistingWalletCommand) -> tuple[WalletDTO, int]:
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.wallet_id,
            user_id=command.user_id,
        )

        return await self.rename_and_emit(wallet_aggregate, command)

    async def rename_and_emit(
        self,
        wallet_aggregate: WalletAggregate,
        command: UpdateExistingWalletCommand,
    ) -> tuple[WalletDTO, int]:
        timestamp_now = datetime.now()
        previous_data = WalletData(
            title=wallet_aggregate.root.title,
            currency_code=wallet_aggregate.root.currency_code,
        )
        wallet_aggregate.rename(new_title=command.new_name, now=timestamp_now)
        updated_wallet, latest_sequence = await self._run_transactions_saga(
            wallet_aggregate=wallet_aggregate,
            previous_state=previous_data,
            timestamp=timestamp_now,
            partition_key=command.user_external_id,
        )
        wallet_dto = wallet_to_dto(
            wallet=updated_wallet,
            balance_amount=wallet_aggregate.balance,
        )

        await self._publish_domain_events(wallet_aggregate)
        return wallet_dto, latest_sequence

    async def _run_transactions_saga(
        self,
        wallet_aggregate: WalletAggregate,
        previous_state: WalletData,
        timestamp: datetime,
        partition_key: str,
    ) -> tuple[WalletEntity, int]:
        wallet_holder: dict[str, WalletEntity] = {}
        persist_rename, undo_rename = self._get_save_unsave_lambdas(
            wallet_holder=wallet_holder,
            wallet_aggregate=wallet_aggregate,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_rename,
                    compensate_action=undo_rename,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WalletUpdated(
                            wallet_id=wallet_aggregate.unique_id,
                            user_id=int(wallet_aggregate.root.user_id),
                            previous_title=previous_state.title,
                            new_title=wallet_aggregate.root.title,
                            updated_at=datetime_to_timestamp(timestamp),
                        ),
                        aggregate_type="wallet",
                        aggregate_id=wallet_aggregate.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        latest_sequence = await saga_coordinator.run_transaction()
        return wallet_holder["wallet"], latest_sequence

    def _get_save_unsave_lambdas(
        self,
        wallet_holder: dict[str, WalletEntity],
        wallet_aggregate: WalletAggregate,
    ) -> tuple[PostgresAction, PostgresAction]:
        previous_title = wallet_aggregate.root.title

        async def persist_rename() -> None:
            wallet_holder["wallet"] = await self._wallet_repository.save_wallet(
                wallet_aggregate.root,
            )

        async def undo_rename() -> None:
            wallet_aggregate.root.rename(previous_title, datetime.now())
            await self._wallet_repository.save_wallet(wallet_aggregate.root)

        return persist_rename, undo_rename
