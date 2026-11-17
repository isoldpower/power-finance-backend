from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Unpack
from uuid import UUID

from kafka_messages import TransactionCreated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.value_objects import (
    CategoryKind,
    TransactionMetadata,
    TransactionOrigin,
    TransactionType,
)
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ..._amount_scale import ensure_amount_scale
from ...dtos import TransactionDTO, container_to_dto, transaction_to_dto
from ...interfaces import (
    CategoryRepository,
    TransactionRepository,
)
from .._category_resolution import CategoryResolverMixin, category_event_fields
from .._ledger_command_base import LedgerCommandHandlerBase, LedgerRepositoryOverrides
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
    category_id: UUID | None = None
    evidence_url: str | None = None
    chain_id: UUID | None = None
    transaction_id: UUID | None = None


class CreateTransactionCommandHandler(
    LedgerCommandHandlerBase[TransactionDTO], CategoryResolverMixin
):
    def __init__(
        self,
        category_repository: CategoryRepository | None = None,
        **repositories: Unpack[LedgerRepositoryOverrides],
    ) -> None:
        super().__init__(**repositories)
        self.use_category_repository(category_repository)

    async def handle(self, command: CreateTransactionCommand) -> tuple[TransactionDTO, int]:
        container = await self.load_container_aggregate(
            container_id=command.wallet_id,
            user_id=command.user_id,
        )

        await ensure_amount_scale(command.amount, container.currency_code)
        category = await self.resolve_category(
            command.category_id,
            command.user_id,
            CategoryKind.TRANSACTION,
        )
        aggregate = build_transaction(
            user_id=command.user_id,
            container=container.as_reference(),
            metadata=TransactionMetadata(
                name=command.name,
                category=category,
                evidence_url=command.evidence_url,
                origin=command.origin,
                chain_id=command.chain_id,
            ),
            amount=command.amount,
            transaction_type=command.transaction_type,
            created_at=datetime.now(),
            transaction_id=command.transaction_id,
        )
        container.record(aggregate.origin_flow)

        latest_version = await self._persist(
            aggregate,
            command.user_external_id,
            container.currency_code,
        )
        transaction_dto = transaction_to_dto(
            aggregate,
            container_to_dto(container.as_reference()),
        )

        await self._publish_domain_events(aggregate)
        return transaction_dto, latest_version

    async def _persist(
        self,
        aggregate: TransactionAggregate,
        partition_key: str,
        currency_code: str,
    ) -> int:
        return await run_transaction_saga(
            postgres_steps=[
                persist_transaction_step(
                    self._transaction_repository,
                    aggregate,
                )
            ],
            flows=aggregate.flows,
            entries=[
                transaction_created_entry(
                    aggregate,
                    partition_key,
                    currency_code,
                )
            ],
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


def transaction_created_entry(
    aggregate: TransactionAggregate,
    partition_key: str,
    currency_code: str,
):
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
            **category_event_fields(root.category),
            evidence_url=root.evidence_url or "",
            origin=str(root.origin),
            chain_id=str(root.chain_id) if root.chain_id else "",
            currency_code=currency_code,
        ),
        aggregate_type="transaction",
        aggregate_id=aggregate.unique_id,
        partition_key=partition_key,
    )
