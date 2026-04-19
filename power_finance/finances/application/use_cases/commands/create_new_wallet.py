from dataclasses import dataclass

from finances.domain.entities import Wallet
from finances.domain.exceptions import UnsupportedCurrencyError

from ..use_case_base import UseCaseEvently
from ..decorators import atomic_evently_command
from ...bootstrap import get_repository_registry
from ...dtos import WalletDTO
from ...dto_builders import wallet_to_dto
from ...interfaces import WalletRepository, CurrencyRepository


@dataclass(frozen=True)
class CreateNewWalletCommand:
    user_id: int
    name: str
    currency: str


class CreateNewWalletCommandHandler(UseCaseEvently):
    wallet_repository: WalletRepository
    currency_repository: CurrencyRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
    ):
        super().__init__()
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository
        self.currency_repository = currency_repository or registry.currency_repository

    @atomic_evently_command()
    async def handle(self, command: CreateNewWalletCommand) -> WalletDTO:
        currency_code = command.currency.upper()
        if not await self.currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        wallet = Wallet.create(
            user_id=command.user_id,
            name=command.name,
            currency_code=currency_code,
        )
        created_wallet = await self.wallet_repository.create_wallet(wallet)

        return wallet_to_dto(created_wallet)
