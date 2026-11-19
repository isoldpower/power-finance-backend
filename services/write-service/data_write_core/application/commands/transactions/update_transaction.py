from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from kafka_messages import TransactionUpdated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp

from ..._amount_scale import ensure_amount_scale
from ...dtos import TransactionDTO, transaction_to_dto
from .._ledger_command_base import LoadedTransactionCommandHandlerBase
from .transaction_saga import run_transaction_saga


@dataclass(frozen=True)
class UpdateTransactionCommand:
    user_id: int
    user_external_id: str
    transaction_id: UUID
    new_amount: Decimal


class UpdateTransactionCommandHandler(LoadedTransactionCommandHandlerBase[TransactionDTO]):
    async def handle(self, command: UpdateTransactionCommand) -> tuple[TransactionDTO, int]:
        aggregate = await self.load_transaction_aggregate(
            transaction_id=command.transaction_id,
            user_id=command.user_id,
        )
        container_dto = await self.load_container_dto(
            container_id=aggregate.root.container_id,
            user_id=command.user_id,
        )
        await ensure_amount_scale(command.new_amount, container_dto.currency)

        previous_amount = aggregate.amount
        signed_amount = TransactionEntity.signed(command.new_amount, aggregate.type)

        moment = datetime.now()
        adjusting_flow = aggregate.adjust(signed_amount, now=moment)
        if adjusting_flow is None:
            return transaction_to_dto(aggregate, container_dto), 0

        latest_version = await self._persist(
            aggregate,
            previous_amount=previous_amount,
            timestamp=moment,
            partition_key=command.user_external_id,
        )

        await self._publish_domain_events(aggregate)
        return transaction_to_dto(aggregate, container_dto), latest_version

    async def _persist(
        self,
        aggregate: TransactionAggregate,
        previous_amount: Decimal,
        timestamp: datetime,
        partition_key: str,
    ) -> int:
        root = aggregate.root

        return await run_transaction_saga(
            postgres_steps=[],
            flows=[aggregate.flows[-1]],
            entries=[
                build_outbox_entry(
                    TransactionUpdated(
                        transaction_id=aggregate.unique_id,
                        wallet_id=str(root.container_id),
                        user_id=int(root.user_id),
                        previous_amount=str(previous_amount),
                        new_amount=str(aggregate.amount),
                        updated_at=datetime_to_timestamp(timestamp),
                        chain_id=str(root.chain_id) if root.chain_id else "",
                    ),
                    aggregate_type="transaction",
                    aggregate_id=aggregate.unique_id,
                    partition_key=partition_key,
                )
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )
