from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from kafka_messages import TransactionCreated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.value_objects import (
    TransactionMetadata,
    TransactionOrigin,
    TransactionType,
)
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ..._amount_scale import ensure_amount_scale
from ...bootstrap import get_repository_registry
from ...dtos import TransactionDTO, container_to_dto, transaction_to_dto
from ...interfaces import (
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..loader_mixins import LoadContainerMixin
from .transaction_factory import build_transaction
from .transaction_saga import run_transaction_saga


@dataclass(frozen=True)
class CreateTransactionCommand:
    user_id: int
    user_external_id: str
    wallet_id: UUID
    amount: Decimal
    name: str
    transaction_type: TransactionType
    origin: TransactionOrigin = TransactionOrigin.MANUAL
    category: str | None = None
    evidence_url: str | None = None
    chain_id: UUID | None = None


class CreateTransactionCommandHandler(CommandHandlerBase[TransactionDTO], LoadContainerMixin):
    def __init__(
        self,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
        goal_repository: GoalRepository | None = None,
        container_repository: MoneyContainerRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        wallet_repository = wallet_repository or registry.wallet_repository
        money_flow_repository = money_flow_repository or registry.money_flow_repository
        outbox_repository = outbox_repository or registry.outbox_repository
        transaction_repository = transaction_repository or registry.transaction_repository
        goal_repository = goal_repository or registry.goal_repository
        container_repository = container_repository or registry.money_container_repository

        LoadContainerMixin.__init__(
            self,
            container_repository=container_repository,
            wallet_repository=wallet_repository,
            goal_repository=goal_repository,
            money_flow_repository=money_flow_repository,
        )

        self._money_flow_repository = money_flow_repository
        self._wallet_repository = wallet_repository
        self._outbox_repository = outbox_repository
        self._transaction_repository = transaction_repository

    async def handle(self, command: CreateTransactionCommand) -> tuple[TransactionDTO, int]:
        container = await self.load_container_aggregate(
            container_id=command.wallet_id,
            user_id=command.user_id,
        )

        await ensure_amount_scale(command.amount, container.currency_code)
        aggregate = build_transaction(
            user_id=command.user_id,
            container=container.as_reference(),
            metadata=TransactionMetadata(
                name=command.name,
                category=command.category,
                evidence_url=command.evidence_url,
                origin=command.origin,
                chain_id=command.chain_id,
            ),
            amount=command.amount,
            transaction_type=command.transaction_type,
            created_at=datetime.now(),
        )
        container.record(aggregate.origin_flow)

        latest_version = await self._persist(
            aggregate,
            command.user_external_id,
        )
        transaction_dto = transaction_to_dto(
            aggregate,
            container_to_dto(container.as_reference()),
        )

        await self._publish_domain_events(aggregate)
        return transaction_dto, latest_version

    async def _persist(self, aggregate: TransactionAggregate, partition_key: str) -> int:
        return await run_transaction_saga(
            postgres_steps=[
                persist_transaction_step(
                    self._transaction_repository,
                    aggregate,
                )
            ],
            flows=aggregate.flows,
            entries=[transaction_created_entry(aggregate, partition_key)],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )


def persist_transaction_step(
    repository: TransactionRepository,
    aggregate: TransactionAggregate,
) -> PostgresWriteStep:
    async def forward() -> None:
        await repository.create_transaction(aggregate.root)

    async def compensate() -> None:
        await repository.hard_delete_transaction(UUID(aggregate.unique_id))

    return PostgresWriteStep(
        forward_action=forward,
        compensate_action=compensate,
    )


def transaction_created_entry(aggregate: TransactionAggregate, partition_key: str):
    root = aggregate.root

    return build_outbox_entry(
        TransactionCreated(
            transaction_id=aggregate.unique_id,
            wallet_id=str(root.container_id),
            container_kind=str(root.container_kind),
            user_id=int(root.user_id),
            amount=str(aggregate.amount),
            created_at=datetime_to_timestamp(root.created_at),
            name=root.name,
            category=root.category or "",
            evidence_url=root.evidence_url or "",
            origin=str(root.origin),
            chain_id=str(root.chain_id) if root.chain_id else "",
        ),
        aggregate_type="transaction",
        aggregate_id=aggregate.unique_id,
        partition_key=partition_key,
    )
