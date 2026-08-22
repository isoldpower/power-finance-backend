from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.services import ChainNode, chain_flows, order_chain
from data_write_core.domain.value_objects import (
    TransactionMetadata,
    TransactionOrigin,
    TransactionType,
)
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ..._amount_scale import ensure_amount_scale
from ...bootstrap import get_repository_registry
from ...dtos import (
    TransactionChainDTO,
    WalletDTO,
    transaction_to_dto,
)
from ...interfaces import (
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..loaded_wallets import LoadedWallets
from ..loader_mixins import LoadWalletMixin
from ..transactions.create_transaction import (
    persist_transaction_step,
    transaction_created_entry,
)
from ..transactions.transaction_factory import build_transaction
from ..transactions.transaction_saga import run_transaction_saga


@dataclass(frozen=True)
class ChainEntryCommand:
    temporary_id: str
    wallet_id: UUID
    amount: Decimal
    name: str
    transaction_type: TransactionType
    after: str | None = None
    origin: TransactionOrigin = TransactionOrigin.MANUAL
    category: str | None = None
    evidence_url: str | None = None


@dataclass(frozen=True)
class CreateTransactionChainCommand:
    user_id: int
    user_external_id: str
    entries: list[ChainEntryCommand] = field(default_factory=list)


class CreateTransactionChainCommandHandler(
    CommandHandlerBase[TransactionChainDTO], LoadWalletMixin
):
    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        wallet_repository: WalletRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if (
            transaction_repository is None
            or money_flow_repository is None
            or wallet_repository is None
            or outbox_repository is None
        ):
            registry = get_repository_registry()
            transaction_repository = transaction_repository or registry.transaction_repository
            money_flow_repository = money_flow_repository or registry.money_flow_repository
            wallet_repository = wallet_repository or registry.wallet_repository
            outbox_repository = outbox_repository or registry.outbox_repository
        LoadWalletMixin.__init__(self, wallet_repository, money_flow_repository)

        self._transaction_repository = transaction_repository
        self._money_flow_repository = money_flow_repository
        self._wallet_repository = wallet_repository
        self._outbox_repository = outbox_repository

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

        chain_id = uuid4()
        committed_at = datetime.now()
        aggregates, wallet_dtos = await self._build_aggregates(
            command,
            commit_order=commit_order,
            chain_id=chain_id,
            committed_at=committed_at,
        )
        latest_version = await self._persist(
            aggregates,
            chain_id=chain_id,
            user_id=command.user_id,
            committed_at=committed_at,
            partition_key=command.user_external_id,
        )
        await self._publish_domain_events(*aggregates)

        return (
            TransactionChainDTO(
                chain_id=chain_id,
                transactions=[
                    transaction_to_dto(
                        aggregate,
                        wallet_dtos[str(aggregate.root.wallet_id)],
                    )
                    for aggregate in aggregates
                ],
            ),
            latest_version,
        )

    async def _build_aggregates(
        self,
        command: CreateTransactionChainCommand,
        commit_order: list[int],
        chain_id: UUID,
        committed_at: datetime,
    ) -> tuple[list[TransactionAggregate], dict[str, WalletDTO]]:
        wallets = LoadedWallets(loader=self, user_id=command.user_id)
        aggregates = [
            await self._build_entry(
                command.entries[position],
                wallets=wallets,
                user_id=command.user_id,
                chain_id=chain_id,
                committed_at=committed_at,
            )
            for position in commit_order
        ]

        return aggregates, wallets.as_dtos()

    async def _build_entry(
        self,
        entry: ChainEntryCommand,
        wallets: LoadedWallets,
        user_id: int,
        chain_id: UUID,
        committed_at: datetime,
    ) -> TransactionAggregate:
        wallet = await wallets.get(entry.wallet_id)
        await ensure_amount_scale(entry.amount, wallet.root.currency_code)

        aggregate = build_transaction(
            user_id=user_id,
            wallet_id=entry.wallet_id,
            metadata=_metadata_of(entry, chain_id),
            amount=entry.amount,
            transaction_type=entry.transaction_type,
            created_at=committed_at,
        )
        wallet.record(aggregate.origin_flow)

        return aggregate

    async def _persist(
        self,
        aggregates: list[TransactionAggregate],
        chain_id: UUID,
        user_id: int,
        committed_at: datetime,
        partition_key: str,
    ) -> int:
        repository = self._transaction_repository
        steps: list[PostgresWriteStep] = [
            self._chain_row_step(
                chain_id=chain_id,
                user_id=user_id,
                committed_at=committed_at,
            )
        ]
        steps.extend(persist_transaction_step(repository, aggregate) for aggregate in aggregates)

        return await run_transaction_saga(
            postgres_steps=steps,
            flows=chain_flows(aggregates),
            entries=[
                transaction_created_entry(aggregate, partition_key) for aggregate in aggregates
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


def _metadata_of(entry: ChainEntryCommand, chain_id: UUID) -> TransactionMetadata:
    return TransactionMetadata(
        name=entry.name,
        category=entry.category,
        evidence_url=entry.evidence_url,
        origin=entry.origin,
        chain_id=chain_id,
    )
