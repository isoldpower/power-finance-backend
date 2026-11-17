from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import TransactionUpdated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.services import bind_to_chain
from data_write_core.domain.value_objects import OutboxEntry
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ...interfaces import MoneyFlowRepository, TransactionRepository
from ..transactions.create_transaction import (
    persist_transaction_step,
    transaction_created_entry,
)


@dataclass(frozen=True)
class ChainExistingEntryCommand:
    temporary_id: str
    transaction_id: UUID
    after: str | None = None


async def load_bound_member(
    transaction_repository: TransactionRepository,
    money_flow_repository: MoneyFlowRepository,
    transaction_id: UUID,
    user_id: int,
    chain_id: UUID,
    bound_at: datetime,
) -> TransactionAggregate:
    transaction = await transaction_repository.get_user_transaction_by_id(
        transaction_id=transaction_id,
        user_id=user_id,
    )
    bind_to_chain(transaction, chain_id, bound_at)

    return TransactionAggregate(
        transaction_entity=transaction,
        flows=await money_flow_repository.get_flows_for_transaction(transaction_id),
    )


def bind_member_step(
    repository: TransactionRepository,
    aggregate: TransactionAggregate,
) -> PostgresWriteStep:
    root = aggregate.root

    async def forward() -> None:
        await repository.save_transaction(root)

    async def compensate() -> None:
        root.leave_chain(datetime.now())
        await repository.save_transaction(root)

    return PostgresWriteStep(
        forward_action=forward,
        compensate_action=compensate,
    )


def chain_joined_entry(
    aggregate: TransactionAggregate,
    partition_key: str,
    bound_at: datetime,
) -> OutboxEntry:
    root = aggregate.root

    return build_outbox_entry(
        TransactionUpdated(
            transaction_id=aggregate.unique_id,
            wallet_id=str(root.container_id),
            user_id=int(root.user_id),
            previous_amount=str(aggregate.amount),
            new_amount=str(aggregate.amount),
            updated_at=datetime_to_timestamp(bound_at),
            chain_id=str(root.chain_id) if root.chain_id else "",
        ),
        aggregate_type="transaction",
        aggregate_id=aggregate.unique_id,
        partition_key=partition_key,
    )


@dataclass(frozen=True)
class ChainMember(ABC):
    aggregate: TransactionAggregate

    @property
    @abstractmethod
    def ledger_aggregates(self) -> list[TransactionAggregate]:
        raise NotImplementedError()

    @abstractmethod
    def write_step(self, repository: TransactionRepository) -> PostgresWriteStep:
        raise NotImplementedError()

    @abstractmethod
    def outbox_entry(
        self, partition_key: str, committed_at: datetime, currency: str
    ) -> OutboxEntry:
        raise NotImplementedError()


class BoundChainMember(ChainMember):
    @property
    def ledger_aggregates(self) -> list[TransactionAggregate]:
        return []

    def write_step(self, repository: TransactionRepository) -> PostgresWriteStep:
        return bind_member_step(repository, self.aggregate)

    def outbox_entry(
        self, partition_key: str, committed_at: datetime, currency: str
    ) -> OutboxEntry:
        return chain_joined_entry(self.aggregate, partition_key, committed_at)


class CreatedChainMember(ChainMember):
    @property
    def ledger_aggregates(self) -> list[TransactionAggregate]:
        return [self.aggregate]

    def write_step(self, repository: TransactionRepository) -> PostgresWriteStep:
        return persist_transaction_step(repository, self.aggregate)

    def outbox_entry(
        self, partition_key: str, committed_at: datetime, currency: str
    ) -> OutboxEntry:
        return transaction_created_entry(self.aggregate, partition_key, currency)
