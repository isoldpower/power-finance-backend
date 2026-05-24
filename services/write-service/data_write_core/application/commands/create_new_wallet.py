from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.exceptions import UnsupportedCurrencyError
from data_write_core.domain.value_objects import WalletData
from data_write_core.infrastructure.outbox_saga import (
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
    SagaCoordinator,
    WalletCreatedOutboxEvent,
)

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import CurrencyRepository, OutboxRepository, WalletRepository
from ._command_base import CommandHandlerBase


@dataclass(frozen=True)
class CreateNewWalletCommand:
    user_id: int
    name: str
    currency: str


class CreateNewWalletCommandHandler(CommandHandlerBase[WalletDTO]):
    _wallet_repository: WalletRepository
    _currency_repository: CurrencyRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self._wallet_repository = wallet_repository or registry.wallet_repository
        self._currency_repository = currency_repository or registry.currency_repository
        self._outbox_repository = outbox_repository or registry.outbox_repository

    async def handle(self, command: CreateNewWalletCommand) -> tuple[WalletDTO, int]:
        currency_code = command.currency.upper()
        if not await self._currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        timestamp_now = datetime.now()
        new_wallet = WalletEntity.create(
            id=str(uuid4()),
            data=WalletData(
                currency_code=currency_code,
                title=command.name,
            ),
            user_id=str(command.user_id),
            created_at=timestamp_now,
            updated_at=timestamp_now,
        )
        persisted_wallet, write_version = await self._run_transactions_saga(new_wallet)

        await self._publish_domain_events(new_wallet)
        return wallet_to_dto(persisted_wallet), write_version

    async def _run_transactions_saga(self, new_wallet: WalletEntity) -> tuple[WalletEntity, int]:
        created_wallet_holder: dict[str, WalletEntity] = {}
        persist_wallet, undo_persisted_wallet = self._get_save_unsave_lambdas(
            wallet_holder=created_wallet_holder,
            created_wallet=new_wallet,
        )

        saga_coordinator = SagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_wallet,
                    compensate_action=undo_persisted_wallet,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                events=[
                    WalletCreatedOutboxEvent(
                        wallet_id=UUID(new_wallet.unique_id),
                        user_id=int(new_wallet.user_id),
                        title=new_wallet.title,
                        currency_code=new_wallet.currency_code,
                        created_at=new_wallet.created_at,
                    )
                ],
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return created_wallet_holder["wallet"], outbox_version

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
