from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.utils import timezone

from finances.domain.entities import Wallet
from finances.domain.exceptions import UnsupportedCurrencyError
from finances.domain.value_objects import Money

from ...bootstrap import get_repository_registry
from ...dtos import WalletDTO
from ...dto_builders import wallet_to_dto
from ...interfaces import WalletRepository, CurrencyRepository


@dataclass(frozen=True)
class CreateNewWalletCommand:
    user_id: int
    name: str
    balance_amount: Decimal
    currency: str
    credit: bool


class CreateNewWalletCommandHandler:
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

    @transaction.atomic
    def handle(self, command: CreateNewWalletCommand) -> WalletDTO:
        currency_code = command.currency.upper()
        if not self.currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        wallet = Wallet(
            id = uuid4(),
            user_id = command.user_id,
            name = command.name,
            balance = Money(
                amount=command.balance_amount,
                currency_code=command.currency,
            ),
            credit = command.credit,
            created_at = timezone.now(),
            updated_at = timezone.now(),
            deleted_at = None,
        )

        created_wallet = self.wallet_repository.create_wallet(wallet)

        return wallet_to_dto(created_wallet)
