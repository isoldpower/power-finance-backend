from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.exceptions import UnsupportedCurrencyError
from data_write_core.domain.value_objects import WalletData

from ..bootstrap import get_repository_registry
from ..dtos import WalletDTO, wallet_to_dto
from ..interfaces import CurrencyRepository, WalletRepository
from ._command_base import CommandHandlerBase
from ._decorators import atomic_command


@dataclass(frozen=True)
class CreateNewWalletCommand:
    user_id: int
    name: str
    currency: str


class CreateNewWalletCommandHandler(CommandHandlerBase):
    _wallet_repository: WalletRepository
    _currency_repository: CurrencyRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self._wallet_repository = wallet_repository or registry.wallet_repository
        self._currency_repository = currency_repository or registry.currency_repository

    @atomic_command()
    async def handle(self, command: CreateNewWalletCommand) -> WalletDTO:
        currency_code = command.currency.upper()
        if not await self._currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        timestamp = datetime.now()
        wallet = WalletEntity.create(
            id=str(uuid4()),
            data=WalletData(
                currency_code=currency_code,
                title=command.name,
            ),
            user_id=str(command.user_id),
            created_at=timestamp,
            updated_at=timestamp,
        )
        created_wallet = await self._wallet_repository.create_wallet(wallet)

        await self._publish_events(wallet)
        return wallet_to_dto(created_wallet)
