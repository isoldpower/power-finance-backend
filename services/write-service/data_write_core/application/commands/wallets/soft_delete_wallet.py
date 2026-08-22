from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import WalletDeleted

from data_write_core.domain.aggregates import WalletAggregate
from data_write_core.domain.entities import WalletEntity
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import WalletDTO, wallet_to_dto
from ...interfaces import MoneyFlowRepository, OutboxRepository, WalletRepository
from ..command_base import CommandHandlerBase
from ..loader_mixins import LoadWalletMixin


@dataclass(frozen=True)
class SoftDeleteWalletCommand:
    user_id: int
    user_external_id: str
    wallet_id: UUID


class SoftDeleteWalletCommandHandler(CommandHandlerBase[WalletDTO], LoadWalletMixin):
    _wallet_repository: WalletRepository
    _transaction_repository: MoneyFlowRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        wallet_repository = wallet_repository or registry.wallet_repository
        money_flow_repository = money_flow_repository or registry.money_flow_repository
        outbox_repository = outbox_repository or registry.outbox_repository

        LoadWalletMixin.__init__(self, wallet_repository, money_flow_repository)

        self._wallet_repository = wallet_repository
        self._transaction_repository = money_flow_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: SoftDeleteWalletCommand) -> tuple[WalletDTO, int]:
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.wallet_id,
            user_id=command.user_id,
        )

        timestamp_now = datetime.now()
        wallet_aggregate.soft_delete(now=timestamp_now)
        saved_wallet, latest_sequence = await self._run_transactions_saga(
            wallet_aggregate=wallet_aggregate,
            timestamp_now=timestamp_now,
            partition_key=command.user_external_id,
        )
        wallet_dto = wallet_to_dto(saved_wallet, balance_amount=wallet_aggregate.balance)

        await self._publish_domain_events(wallet_aggregate)
        return wallet_dto, latest_sequence

    async def _run_transactions_saga(
        self,
        wallet_aggregate: WalletAggregate,
        timestamp_now: datetime,
        partition_key: str,
    ) -> tuple[WalletEntity, int]:
        saved_wallet_holder: dict[str, WalletEntity] = {}
        persist_soft_delete, undo_soft_delete = self._get_save_unsave_lambdas(
            wallet_holder=saved_wallet_holder,
            wallet_aggregate=wallet_aggregate,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_soft_delete,
                    compensate_action=undo_soft_delete,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        WalletDeleted(
                            wallet_id=wallet_aggregate.unique_id,
                            user_id=int(wallet_aggregate.root.user_id),
                            deleted_at=datetime_to_timestamp(timestamp_now),
                        ),
                        aggregate_type="wallet",
                        aggregate_id=wallet_aggregate.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        latest_sequence = await saga_coordinator.run_transaction()
        return saved_wallet_holder["wallet"], latest_sequence

    def _get_save_unsave_lambdas(
        self,
        wallet_holder: dict[str, WalletEntity],
        wallet_aggregate: WalletAggregate,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_soft_delete() -> None:
            wallet_holder["wallet"] = await self._wallet_repository.save_wallet(
                wallet_aggregate.root,
            )

        async def undo_soft_delete() -> None:
            wallet_aggregate.root.restore(datetime.now())
            await self._wallet_repository.save_wallet(wallet_aggregate.root)

        return persist_soft_delete, undo_soft_delete
