from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Unpack
from uuid import UUID, uuid4

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.services import (
    ChainNode,
    chain_flows,
    ensure_distinct_members,
    order_chain,
)
from data_write_core.domain.value_objects import (
    CategoryKind,
    CategoryReference,
    TransactionMetadata,
    TransactionOrigin,
    TransactionType,
)
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ..._amount_scale import ensure_amount_scale
from ...dtos import (
    MoneyContainerDTO,
    TransactionChainDTO,
    transaction_to_dto,
)
from ...interfaces import (
    CategoryRepository,
)
from .._category_resolution import CategoryResolverMixin
from .._ledger_command_base import LedgerCommandHandlerBase, LedgerRepositoryOverrides
from .._loaded_containers import LoadedContainers
from ..transactions.transaction_factory import build_transaction
from ..transactions.transaction_saga import run_transaction_saga
from ._chain_members import (
    BoundChainMember,
    ChainExistingEntryCommand,
    ChainMember,
    CreatedChainMember,
    load_bound_member,
)


@dataclass(frozen=True)
class ChainEntryCommand:
    temporary_id: str
    wallet_id: UUID
    amount: Decimal
    name: str
    transaction_type: TransactionType
    after: str | None = None
    origin: TransactionOrigin = TransactionOrigin.MANUAL
    category_id: UUID | None = None
    evidence_url: str | None = None


ChainMemberCommand = ChainEntryCommand | ChainExistingEntryCommand


@dataclass(frozen=True)
class CreateTransactionChainCommand:
    user_id: int
    user_external_id: str
    entries: list[ChainMemberCommand] = field(default_factory=list)


class CreateTransactionChainCommandHandler(
    LedgerCommandHandlerBase[TransactionChainDTO], CategoryResolverMixin
):
    def __init__(
        self,
        category_repository: CategoryRepository | None = None,
        **repositories: Unpack[LedgerRepositoryOverrides],
    ) -> None:
        super().__init__(**repositories)
        self.use_category_repository(category_repository)

    async def handle(
        self,
        command: CreateTransactionChainCommand,
    ) -> tuple[TransactionChainDTO, int]:
        commit_order = order_chain(
            [
                ChainNode(temporary_id=entry.temporary_id, after=entry.after)
                for entry in command.entries
            ]
        )

        ensure_distinct_members(
            [
                entry.transaction_id
                for entry in command.entries
                if isinstance(entry, ChainExistingEntryCommand)
            ]
        )

        chain_id = uuid4()
        committed_at = datetime.now()
        members, container_dtos = await self._build_members(
            command,
            commit_order=commit_order,
            chain_id=chain_id,
            committed_at=committed_at,
        )
        aggregates = [member.aggregate for member in members]
        latest_version = await self._persist(
            members,
            chain_id=chain_id,
            user_id=command.user_id,
            committed_at=committed_at,
            partition_key=command.user_external_id,
            container_dtos=container_dtos,
        )
        await self._publish_domain_events(*aggregates)

        return (
            TransactionChainDTO(
                chain_id=chain_id,
                transactions=[
                    transaction_to_dto(
                        aggregate,
                        container_dtos[str(aggregate.root.container_id)],
                    )
                    for aggregate in aggregates
                ],
            ),
            latest_version,
        )

    async def _build_members(
        self,
        command: CreateTransactionChainCommand,
        commit_order: list[int],
        chain_id: UUID,
        committed_at: datetime,
    ) -> tuple[list[ChainMember], dict[str, MoneyContainerDTO]]:
        containers = LoadedContainers(
            loader=self,
            user_id=command.user_id,
        )
        members = [
            await self._build_member(
                command.entries[position],
                containers=containers,
                user_id=command.user_id,
                chain_id=chain_id,
                committed_at=committed_at,
            )
            for position in commit_order
        ]

        return members, containers.as_dtos()

    async def _build_member(
        self,
        entry: ChainMemberCommand,
        containers: LoadedContainers,
        user_id: int,
        chain_id: UUID,
        committed_at: datetime,
    ) -> ChainMember:
        if isinstance(entry, ChainExistingEntryCommand):
            bound_aggregate = await load_bound_member(
                self._transaction_repository,
                self._money_flow_repository,
                transaction_id=entry.transaction_id,
                user_id=user_id,
                chain_id=chain_id,
                bound_at=committed_at,
            )
            await containers.get(bound_aggregate.root.container_id)

            return BoundChainMember(aggregate=bound_aggregate)

        created_aggregate = await self._build_entry(
            entry,
            containers=containers,
            user_id=user_id,
            chain_id=chain_id,
            committed_at=committed_at,
        )

        return CreatedChainMember(aggregate=created_aggregate)

    async def _build_entry(
        self,
        entry: ChainEntryCommand,
        containers: LoadedContainers,
        user_id: int,
        chain_id: UUID,
        committed_at: datetime,
    ) -> TransactionAggregate:
        container = await containers.get(entry.wallet_id)
        await ensure_amount_scale(entry.amount, container.currency_code)
        category = await self.resolve_category(entry.category_id, user_id, CategoryKind.TRANSACTION)

        aggregate = build_transaction(
            user_id=user_id,
            container=container.as_reference(),
            metadata=_metadata_of(entry, chain_id, category),
            amount=entry.amount,
            transaction_type=entry.transaction_type,
            created_at=committed_at,
        )
        container.record(aggregate.origin_flow)

        return aggregate

    async def _persist(
        self,
        members: list[ChainMember],
        chain_id: UUID,
        user_id: int,
        committed_at: datetime,
        partition_key: str,
        container_dtos: dict[str, MoneyContainerDTO],
    ) -> int:
        repository = self._transaction_repository
        steps: list[PostgresWriteStep] = [
            self._chain_row_step(
                chain_id=chain_id,
                user_id=user_id,
                committed_at=committed_at,
            )
        ]
        steps.extend(member.write_step(repository) for member in members)

        return await run_transaction_saga(
            postgres_steps=steps,
            flows=chain_flows(
                [aggregate for member in members for aggregate in member.ledger_aggregates]
            ),
            entries=[
                member.outbox_entry(
                    partition_key,
                    committed_at,
                    currency_of(member.aggregate, container_dtos),
                )
                for member in members
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )

    def _chain_row_step(
        self,
        chain_id: UUID,
        user_id: int,
        committed_at: datetime,
    ) -> PostgresWriteStep:
        repository = self._transaction_repository

        async def create_chain_row() -> None:
            await repository.create_chain(
                chain_id=chain_id,
                user_id=user_id,
                created_at=committed_at,
            )

        async def undo_chain_row() -> None:
            await repository.hard_delete_chain(chain_id)

        return PostgresWriteStep(
            forward_action=create_chain_row,
            compensate_action=undo_chain_row,
        )


def currency_of(
    aggregate: TransactionAggregate,
    container_dtos: dict[str, MoneyContainerDTO],
) -> str:
    return container_dtos[str(aggregate.root.container_id)].currency


def _metadata_of(
    entry: ChainEntryCommand,
    chain_id: UUID,
    category: CategoryReference | None,
) -> TransactionMetadata:
    return TransactionMetadata(
        name=entry.name,
        category=category,
        evidence_url=entry.evidence_url,
        origin=entry.origin,
        chain_id=chain_id,
    )
