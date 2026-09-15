from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from kafka_messages import TransactionDeleted, TransactionUpdated

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ...bootstrap import get_repository_registry
from ...dtos import TransactionDTO, transaction_to_dto
from ...interfaces import (
    GoalRepository,
    MoneyContainerRepository,
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..loader_mixins import LoadContainerMixin, LoadTransactionMixin
from .transaction_saga import run_transaction_saga


class ResolvedRepositories(NamedTuple):
    transaction_repository: TransactionRepository
    money_flow_repository: MoneyFlowRepository
    wallet_repository: WalletRepository
    outbox_repository: OutboxRepository
    goal_repository: GoalRepository
    container_repository: MoneyContainerRepository


def _resolve_repositories(
    *,
    transaction_repository: TransactionRepository | None,
    money_flow_repository: MoneyFlowRepository | None,
    wallet_repository: WalletRepository | None,
    outbox_repository: OutboxRepository | None,
    goal_repository: GoalRepository | None,
    container_repository: MoneyContainerRepository | None,
) -> ResolvedRepositories:
    """Fall back to the bootstrapped registry only for what the caller left out.

    A handler given every collaborator — as tests do — never touches the registry,
    so it does not need the application to be bootstrapped to be constructible.
    """
    given = (
        transaction_repository,
        money_flow_repository,
        wallet_repository,
        outbox_repository,
        goal_repository,
        container_repository,
    )
    if all(repository is not None for repository in given):
        return ResolvedRepositories(*given)  # type: ignore[arg-type]

    registry = get_repository_registry()

    return ResolvedRepositories(
        transaction_repository=transaction_repository or registry.transaction_repository,
        money_flow_repository=money_flow_repository or registry.money_flow_repository,
        wallet_repository=wallet_repository or registry.wallet_repository,
        outbox_repository=outbox_repository or registry.outbox_repository,
        goal_repository=goal_repository or registry.goal_repository,
        container_repository=container_repository or registry.money_container_repository,
    )


@dataclass(frozen=True)
class DeleteTransactionCommand:
    transaction_id: UUID
    user_id: int
    user_external_id: str


class DeleteTransactionCommandHandler(
    CommandHandlerBase[TransactionDTO],
    LoadContainerMixin,
    LoadTransactionMixin,
):
    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
        goal_repository: GoalRepository | None = None,
        container_repository: MoneyContainerRepository | None = None,
    ) -> None:
        resolved = _resolve_repositories(
            transaction_repository=transaction_repository,
            money_flow_repository=money_flow_repository,
            wallet_repository=wallet_repository,
            outbox_repository=outbox_repository,
            goal_repository=goal_repository,
            container_repository=container_repository,
        )
        transaction_repository = resolved.transaction_repository
        money_flow_repository = resolved.money_flow_repository
        wallet_repository = resolved.wallet_repository
        outbox_repository = resolved.outbox_repository
        goal_repository = resolved.goal_repository
        container_repository = resolved.container_repository

        LoadContainerMixin.__init__(
            self,
            container_repository=container_repository,
            wallet_repository=wallet_repository,
            goal_repository=goal_repository,
            money_flow_repository=money_flow_repository,
        )
        LoadTransactionMixin.__init__(
            self,
            transaction_repository,
            money_flow_repository,
        )

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

        chain_version = await self._collapse_chain_if_spent(aggregate, command, moment)

        return transaction_dto, chain_version or latest_version

    async def _collapse_chain_if_spent(
        self,
        aggregate: TransactionAggregate,
        command: DeleteTransactionCommand,
        moment: datetime,
    ) -> int | None:
        """A chain is a relationship between transactions, so one leg is not a chain.

        Cancelling a leg can leave a single survivor; that survivor is released and
        the chain row goes, keeping the write model free of chains nothing joins.
        The read models only record which chain a transaction belongs to, so the
        release reaches them as the survivor's new (empty) chain membership.
        """
        chain_id = aggregate.root.chain_id
        if chain_id is None:
            return None

        survivors = await self._transaction_repository.live_chain_transactions(
            chain_id=chain_id,
            user_id=command.user_id,
        )
        if len(survivors) > 1:
            return None

        if not survivors:
            await self._transaction_repository.delete_chain_row(chain_id)
            return None

        return await self._release_last_leg(
            transaction_id=UUID(survivors[0].unique_id),
            chain_id=chain_id,
            command=command,
            moment=moment,
        )

    async def _release_last_leg(
        self,
        transaction_id: UUID,
        chain_id: UUID,
        command: DeleteTransactionCommand,
        moment: datetime,
    ) -> int | None:
        survivor = await self.load_transaction_aggregate(
            transaction_id=transaction_id,
            user_id=command.user_id,
        )
        root = survivor.root
        if not root.leave_chain(moment):
            return None

        repository = self._transaction_repository

        async def forward() -> None:
            await repository.save_transaction(root)
            await repository.delete_chain_row(chain_id)

        async def compensate() -> None:
            root.chain_id = chain_id
            await repository.save_transaction(root)
            await repository.create_chain(chain_id, command.user_id, root.created_at)

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
                    TransactionUpdated(
                        transaction_id=survivor.unique_id,
                        wallet_id=str(root.container_id),
                        user_id=int(root.user_id),
                        previous_amount=str(survivor.amount),
                        new_amount=str(survivor.amount),
                        updated_at=datetime_to_timestamp(moment),
                        chain_id="",
                    ),
                    aggregate_type="transaction",
                    aggregate_id=survivor.unique_id,
                    partition_key=command.user_external_id,
                )
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )

    async def _present(
        self,
        aggregate: TransactionAggregate,
        user_id: int,
    ) -> TransactionDTO:
        container_dto = await self.load_container_dto(
            container_id=aggregate.root.container_id,
            user_id=user_id,
        )

        return transaction_to_dto(aggregate, container_dto)

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
                PostgresWriteStep(
                    forward_action=forward,
                    compensate_action=compensate,
                )
            ],
            flows=[aggregate.flows[-1]],
            entries=[
                build_outbox_entry(
                    TransactionDeleted(
                        transaction_id=aggregate.unique_id,
                        wallet_id=str(root.container_id),
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
