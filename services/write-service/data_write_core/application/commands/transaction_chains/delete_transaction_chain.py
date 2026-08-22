from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import TransactionDeleted

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.exceptions import TransactionChainNotFoundError
from data_write_core.domain.services import CancelledTransaction, cancel_chain
from data_write_core.domain.value_objects import OutboxEntry
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import PostgresWriteStep

from ...bootstrap import get_repository_registry
from ...dtos import TransactionChainDTO, transaction_to_dto
from ...interfaces import (
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..loaded_wallets import LoadedWallets
from ..loader_mixins import LoadWalletMixin
from ..transactions.transaction_saga import run_transaction_saga

TRANSACTION_AGGREGATE_TYPE = "transaction"


@dataclass(frozen=True)
class DeleteTransactionChainCommand:
    user_id: int
    user_external_id: str
    chain_id: UUID


class DeleteTransactionChainCommandHandler(
    CommandHandlerBase[TransactionChainDTO], LoadWalletMixin
):
    _transaction_repository: TransactionRepository
    _money_flow_repository: MoneyFlowRepository
    _wallet_repository: WalletRepository
    _outbox_repository: OutboxRepository

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
        command: DeleteTransactionChainCommand,
    ) -> tuple[TransactionChainDTO, int]:
        transactions = await self._transaction_repository.get_chain_transactions(
            chain_id=command.chain_id,
            user_id=command.user_id,
        )
        if not transactions:
            raise TransactionChainNotFoundError(command.chain_id)

        aggregates = [
            TransactionAggregate(
                transaction_entity=transaction,
                flows=await self._money_flow_repository.get_flows_for_transaction(
                    UUID(transaction.unique_id)
                ),
            )
            for transaction in transactions
        ]

        cancelled_at = datetime.now()
        cancellations = cancel_chain(aggregates, cancelled_at)

        latest_version = 0
        if cancellations:
            latest_version = await self._persist(
                cancellations,
                cancelled_at=cancelled_at,
                partition_key=command.user_external_id,
            )

        chain_dto = await self._present(command, aggregates)
        await self._publish_domain_events(*aggregates)

        return chain_dto, latest_version

    async def _present(
        self,
        command: DeleteTransactionChainCommand,
        aggregates: list[TransactionAggregate],
    ) -> TransactionChainDTO:
        wallets = LoadedWallets(loader=self, user_id=command.user_id)
        for aggregate in aggregates:
            await wallets.get(aggregate.root.wallet_id)

        wallet_dtos = wallets.as_dtos()
        return TransactionChainDTO(
            chain_id=command.chain_id,
            transactions=[
                transaction_to_dto(aggregate, wallet_dtos[str(aggregate.root.wallet_id)])
                for aggregate in aggregates
            ],
        )

    async def _persist(
        self,
        cancellations: list[CancelledTransaction],
        cancelled_at: datetime,
        partition_key: str,
    ) -> int:
        repository = self._transaction_repository

        return await run_transaction_saga(
            postgres_steps=[
                self._cancel_step(repository, cancellation.transaction)
                for cancellation in cancellations
            ],
            flows=[cancellation.inverse_flow for cancellation in cancellations],
            entries=[
                self._cancelled_entry(cancellation, cancelled_at, partition_key)
                for cancellation in cancellations
            ],
            money_flow_repository=self._money_flow_repository,
            outbox_repository=self._outbox_repository,
        )

    @staticmethod
    def _cancelled_entry(
        cancellation: CancelledTransaction,
        cancelled_at: datetime,
        partition_key: str,
    ) -> OutboxEntry:
        root = cancellation.transaction.root

        return build_outbox_entry(
            TransactionDeleted(
                transaction_id=cancellation.transaction.unique_id,
                wallet_id=str(root.wallet_id),
                user_id=int(root.user_id),
                amount=str(cancellation.outstanding_amount),
                created_at=datetime_to_timestamp(root.created_at),
                deleted_at=datetime_to_timestamp(cancelled_at),
            ),
            aggregate_type=TRANSACTION_AGGREGATE_TYPE,
            aggregate_id=cancellation.transaction.unique_id,
            partition_key=partition_key,
        )

    @staticmethod
    def _cancel_step(
        repository: TransactionRepository,
        aggregate: TransactionAggregate,
    ) -> PostgresWriteStep:
        root = aggregate.root

        async def forward() -> None:
            await repository.save_transaction(root)

        async def compensate() -> None:
            root.restore(datetime.now())
            await repository.save_transaction(root)

        return PostgresWriteStep(
            forward_action=forward,
            compensate_action=compensate,
        )
