from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from kafka_messages import WalletCreated
from saga_pattern_py import SagaStep

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity, WalletEntity
from data_write_core.domain.exceptions import UnsupportedCurrencyError
from data_write_core.domain.value_objects import (
    OutboxEntry,
    TransactionMetadata,
    TransactionOrigin,
    WalletData,
)
from data_write_core.infrastructure.messaging import (
    build_outbox_entry,
    datetime_to_timestamp,
)
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    ImmudbMoneyFlowStep,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ..._amount_scale import ensure_amount_scale
from ...bootstrap import get_repository_registry
from ...dtos import WalletDTO, wallet_to_dto
from ...interfaces import (
    CurrencyRepository,
    MoneyFlowRepository,
    OutboxRepository,
    TransactionRepository,
    WalletRepository,
)
from ..command_base import CommandHandlerBase
from ..transactions.create_transaction import persist_transaction_step, transaction_created_entry
from ..transactions.transaction_factory import build_transaction

OPENING_BALANCE_NAME = "Opening balance"
UNSET = object()


@dataclass(frozen=True)
class CreateNewWalletCommand:
    user_id: int
    user_external_id: str
    name: str
    currency: str
    category: str = ""
    color: str = ""
    zero_balance: Decimal = Decimal("0")
    opening_balance: Decimal | object = UNSET


class CreateNewWalletCommandHandler(CommandHandlerBase[WalletDTO]):
    _wallet_repository: WalletRepository
    _currency_repository: CurrencyRepository
    _money_flow_repository: MoneyFlowRepository
    _transaction_repository: TransactionRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        transaction_repository: TransactionRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self._wallet_repository = wallet_repository or registry.wallet_repository
        self._currency_repository = currency_repository or registry.currency_repository
        self._outbox_repository = outbox_repository or registry.outbox_repository
        self._money_flow_repository = money_flow_repository or registry.money_flow_repository
        self._transaction_repository = transaction_repository or registry.transaction_repository

    async def handle(self, command: CreateNewWalletCommand) -> tuple[WalletDTO, int]:
        currency_code = command.currency.upper()
        if not await self._currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        opening_balance = self._resolve_opening_balance(command)
        await ensure_amount_scale(command.zero_balance, currency_code)
        await ensure_amount_scale(opening_balance, currency_code)

        timestamp_now = datetime.now()
        new_wallet = WalletEntity.create(
            id=str(uuid4()),
            data=WalletData(
                currency_code=currency_code,
                title=command.name,
                category=command.category,
                color=command.color,
                zero_balance=command.zero_balance,
            ),
            user_id=str(command.user_id),
            created_at=timestamp_now,
            updated_at=timestamp_now,
        )

        opening_transaction = (
            build_transaction(
                user_id=command.user_id,
                wallet_id=UUID(new_wallet.unique_id),
                metadata=TransactionMetadata(
                    name=OPENING_BALANCE_NAME,
                    origin=TransactionOrigin.MANUAL,
                ),
                amount=abs(opening_balance),
                transaction_type=TransactionEntity.type_for(opening_balance),
                created_at=timestamp_now,
            )
            if opening_balance != Decimal("0")
            else None
        )

        persisted_wallet, write_version = await self._run_transactions_saga(
            new_wallet,
            opening_transaction=opening_transaction,
            partition_key=command.user_external_id,
        )

        if opening_transaction is not None:
            await self._publish_domain_events(opening_transaction)

        return wallet_to_dto(persisted_wallet, balance_amount=opening_balance), write_version

    @staticmethod
    def _resolve_opening_balance(command: CreateNewWalletCommand) -> Decimal:
        if command.opening_balance is UNSET:
            return command.zero_balance

        assert isinstance(command.opening_balance, Decimal)
        return command.opening_balance

    async def _run_transactions_saga(
        self,
        new_wallet: WalletEntity,
        opening_transaction: TransactionAggregate | None,
        partition_key: str,
    ) -> tuple[WalletEntity, int]:
        created_wallet_holder: dict[str, WalletEntity] = {}
        persist_wallet, undo_persisted_wallet = self._get_save_unsave_lambdas(
            wallet_holder=created_wallet_holder,
            created_wallet=new_wallet,
        )

        steps: list[SagaStep] = [
            PostgresWriteStep(
                forward_action=persist_wallet,
                compensate_action=undo_persisted_wallet,
            ),
        ]
        if opening_transaction is not None:
            steps.append(
                persist_transaction_step(self._transaction_repository, opening_transaction)
            )
            steps.append(
                ImmudbMoneyFlowStep(
                    repository=self._money_flow_repository,
                    transaction=opening_transaction.origin_flow,
                )
            )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=steps,
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=self._outbox_entries(
                    new_wallet,
                    opening_transaction,
                    partition_key=partition_key,
                ),
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return created_wallet_holder["wallet"], outbox_version

    @staticmethod
    def _outbox_entries(
        new_wallet: WalletEntity,
        opening_transaction: TransactionAggregate | None,
        partition_key: str,
    ) -> list[OutboxEntry]:
        entries = [
            build_outbox_entry(
                WalletCreated(
                    wallet_id=new_wallet.unique_id,
                    user_id=int(new_wallet.user_id),
                    title=new_wallet.title,
                    currency_code=new_wallet.currency_code,
                    created_at=datetime_to_timestamp(new_wallet.created_at),
                    category=new_wallet.category,
                    color=new_wallet.color,
                    favorite=new_wallet.favorite,
                    zero_balance=str(new_wallet.zero_balance),
                ),
                aggregate_type="wallet",
                aggregate_id=new_wallet.unique_id,
                partition_key=partition_key,
            )
        ]
        if opening_transaction is None:
            return entries

        entries.append(transaction_created_entry(opening_transaction, partition_key))

        return entries

    def _get_save_unsave_lambdas(
        self,
        wallet_holder: dict[str, WalletEntity],
        created_wallet: WalletEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_wallet() -> None:
            wallet_holder["wallet"] = await self._wallet_repository.create_wallet(
                created_wallet,
            )

        async def undo_persisted_wallet() -> None:
            await self._wallet_repository.hard_delete_wallet(
                UUID(created_wallet.unique_id),
            )

        return persist_wallet, undo_persisted_wallet
