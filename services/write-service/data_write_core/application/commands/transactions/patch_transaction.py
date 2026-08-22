from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import TransactionMetadataUpdated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities.transaction import UNCHANGED
from data_write_core.domain.value_objects import TransactionMetadata
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ...bootstrap import get_repository_registry
from ...dtos import TransactionDTO, transaction_to_dto
from ...interfaces import (
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..loader_mixins import LoadTransactionMixin, LoadWalletMixin
from .transaction_saga import run_transaction_saga


@dataclass(frozen=True)
class PatchTransactionCommand:
    user_id: int
    user_external_id: str
    transaction_id: UUID
    name: str | object = UNCHANGED
    category: str | None | object = UNCHANGED
    evidence_url: str | None | object = UNCHANGED


class PatchTransactionCommandHandler(
    CommandHandlerBase[TransactionDTO], LoadWalletMixin, LoadTransactionMixin
):
    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        transaction_repository = transaction_repository or registry.transaction_repository
        money_flow_repository = money_flow_repository or registry.money_flow_repository
        wallet_repository = wallet_repository or registry.wallet_repository
        outbox_repository = outbox_repository or registry.outbox_repository

        LoadWalletMixin.__init__(self, wallet_repository, money_flow_repository)
        LoadTransactionMixin.__init__(self, transaction_repository, money_flow_repository)

        self._transaction_repository = transaction_repository
        self._money_flow_repository = money_flow_repository
        self._wallet_repository = wallet_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: PatchTransactionCommand) -> tuple[TransactionDTO, int]:
        aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )

        moment = datetime.now()
        snapshot = aggregate.root.snapshot()
        aggregate.update_metadata(
            now=moment,
            name=command.name,
            category=command.category,
            evidence_url=command.evidence_url,
        )

        latest_version = await self._persist(
            aggregate,
            snapshot=snapshot,
            timestamp=moment,
            partition_key=command.user_external_id,
        )
        wallet_dto = await self.load_wallet_dto(
            wallet_id=aggregate.root.wallet_id,
            user_id=command.user_id,
        )
        transaction_dto = transaction_to_dto(aggregate, wallet_dto)

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
                PostgresWriteStep(forward_action=forward, compensate_action=compensate)
            ],
            flows=[],
            entries=[
                build_outbox_entry(
                    TransactionMetadataUpdated(
                        transaction_id=aggregate.unique_id,
                        user_id=int(root.user_id),
                        name=root.name,
                        category=root.category or "",
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
