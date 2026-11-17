from dataclasses import dataclass
from datetime import datetime
from typing import Unpack
from uuid import UUID

from kafka_messages import TransactionMetadataUpdated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities.transaction import UNCHANGED
from data_write_core.domain.value_objects import CategoryKind, TransactionMetadata
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ...dtos import TransactionDTO, transaction_to_dto
from ...interfaces import (
    CategoryRepository,
)
from .._category_resolution import CategoryResolverMixin, category_event_fields
from .._ledger_command_base import LedgerRepositoryOverrides, LoadedTransactionCommandHandlerBase
from .transaction_saga import run_transaction_saga


@dataclass(frozen=True)
class PatchTransactionCommand:
    user_id: int
    user_external_id: str
    transaction_id: UUID
    name: str | object = UNCHANGED
    category_id: UUID | None | object = UNCHANGED
    evidence_url: str | None | object = UNCHANGED


class PatchTransactionCommandHandler(
    LoadedTransactionCommandHandlerBase[TransactionDTO], CategoryResolverMixin
):
    def __init__(
        self,
        category_repository: CategoryRepository | None = None,
        **repositories: Unpack[LedgerRepositoryOverrides],
    ) -> None:
        super().__init__(**repositories)
        self.use_category_repository(category_repository)

    async def handle(self, command: PatchTransactionCommand) -> tuple[TransactionDTO, int]:
        aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )

        category = await self.resolve_category_change(
            command.category_id,
            command.user_id,
            CategoryKind.TRANSACTION,
            unchanged=UNCHANGED,
        )
        moment = datetime.now()
        snapshot = aggregate.root.snapshot()
        aggregate.update_metadata(
            now=moment,
            name=command.name,
            category=category,
            evidence_url=command.evidence_url,
        )

        latest_version = await self._persist(
            aggregate,
            snapshot=snapshot,
            timestamp=moment,
            partition_key=command.user_external_id,
        )
        container_dto = await self.load_container_dto(
            container_id=aggregate.root.container_id,
            user_id=command.user_id,
        )
        transaction_dto = transaction_to_dto(aggregate, container_dto)

        await self._publish_domain_events(aggregate)
        return transaction_dto, latest_version

    async def _persist(
        self,
        aggregate: TransactionAggregate,
        snapshot: TransactionMetadata,
        timestamp: datetime,
        partition_key: str,
    ) -> int:
        repository = self._transaction_repository

        async def forward() -> None:
            await repository.save_transaction(aggregate.root)

        async def compensate() -> None:
            aggregate.restore_metadata(snapshot, datetime.now())
            await repository.save_transaction(aggregate.root)

        root = aggregate.root

        return await run_transaction_saga(
            postgres_steps=[
                PostgresWriteStep(
                    forward_action=forward,
                    compensate_action=compensate,
                )
            ],
            flows=[],
            entries=[
                build_outbox_entry(
                    TransactionMetadataUpdated(
                        transaction_id=aggregate.unique_id,
                        user_id=int(root.user_id),
                        name=root.name,
                        **category_event_fields(root.category),
                        evidence_url=root.evidence_url or "",
                        updated_at=datetime_to_timestamp(timestamp),
                    ),
                    aggregate_type="transaction",
                    aggregate_id=aggregate.unique_id,
                    partition_key=partition_key,
                )
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )
