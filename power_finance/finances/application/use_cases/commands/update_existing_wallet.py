from dataclasses import dataclass
from uuid import UUID
from django.db import transaction

from finances.domain.value_objects import Money
from finances.domain.entities import Wallet
from finances.domain.exceptions import UnsupportedCurrencyError

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, CurrencyRepository


@dataclass
class UpdateExistingWalletCommand:
    wallet_id: str
    user_id: int
    name: str | None = None
    currency: str | None = None
    balance_amount: int | None = None
    credit: bool | None = None


class UpdateExistingWalletCommandHandler:
    wallet_repository: WalletRepository
    currency_repository: CurrencyRepository

    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
    ):
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository
        self.currency_repository = currency_repository or registry.currency_repository

    async def _update_fields(self, wallet: Wallet, command: UpdateExistingWalletCommand) -> Wallet:
        if command.name is not None:
            wallet.name = command.name
        if command.balance_amount is not None or command.currency is not None:
            balance = Money(
                amount=command.balance_amount or wallet.balance.amount,
                currency_code=command.currency or wallet.balance.currency_code
            )
            wallet.balance = balance
        if command.credit is not None:
            wallet.credit = command.credit

        return await self.wallet_repository.save_wallet(wallet)


    @transaction.atomic
    async def handle(self, command: UpdateExistingWalletCommand) -> WalletDTO:
        if command.currency is not None:
            currency_code = command.currency.upper()
            if not await self.currency_repository.currency_code_exists(currency_code):
                raise UnsupportedCurrencyError(currency_code)

        wallet = await self.wallet_repository.get_user_wallet_by_id(
            UUID(command.wallet_id),
            command.user_id
        )
        updated_wallet = await self._update_fields(wallet, command)

        return wallet_to_dto(updated_wallet)