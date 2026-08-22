from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import TransactionDeleted

from data_write_core.domain.aggregates import TransactionAggregate
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
class DeleteTransactionCommand:
    transaction_id: UUID
    user_id: int
    user_external_id: str


class DeleteTransactionCommandHandler(
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

    async def handle(self, command: DeleteTransactionCommand) -> tuple[TransactionDTO, int]:
        aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )

        moment = datetime.now()
        outstanding = aggregate.amount
        inverse_flow = aggregate.cancel(moment)

        if inverse_flow is None:
            return await self._present(aggregate, command.user_id), 0

        latest_version = await self._persist(
            aggregate,
            outstanding=outstanding,
            timestamp=moment,
            partition_key=command.user_external_id,
        )
        transaction_dto = await self._present(aggregate, command.user_id)

        await self._publish_domain_events(aggregate)
        return transaction_dto, latest_version

    async def _present(
        self,
        aggregate: TransactionAggregate,
        user_id: int,
    ) -> TransactionDTO:
        wallet_dto = await self.load_wallet_dto(
            wallet_id=aggregate.root.wallet_id,
            user_id=user_id,
        )

        return transaction_to_dto(aggregate, wallet_dto)

    async def _persist(
        self,
        aggregate: TransactionAggregate,
        outstanding,
        timestamp: datetime,
        partition_key: str,
    ) -> int:
        repository = self._transaction_repository
        root = aggregate.root

        async def forward() -> None:
            await repository.save_transaction(root)

        async def compensate() -> None:
            root.restore(datetime.now())
            await repository.save_transaction(root)

        return await run_transaction_saga(
            postgres_steps=[
                PostgresWriteStep(forward_action=forward, compensate_action=compensate)
            ],
            flows=[aggregate.flows[-1]],
            entries=[
                build_outbox_entry(
                    TransactionDeleted(
                        transaction_id=aggregate.unique_id,
                        wallet_id=str(root.wallet_id),
                        user_id=int(root.user_id),
                        amount=str(outstanding),
                        created_at=datetime_to_timestamp(root.created_at),
                        deleted_at=datetime_to_timestamp(timestamp),
                    ),
                    aggregate_type="transaction",
                    aggregate_id=aggregate.unique_id,
                    partition_key=partition_key,
                )
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )
