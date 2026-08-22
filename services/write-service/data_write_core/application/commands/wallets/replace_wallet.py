from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.exceptions import WalletCurrencyImmutableError

from ...dtos import WalletDTO
from .update_existing_wallet import (
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)


@dataclass(frozen=True)
class ReplaceWalletCommand:
    user_id: int
    user_external_id: str
    wallet_id: UUID
    name: str
    currency_code: str
    category: str = ""
    color: str = ""
    favorite: bool = False
    zero_balance: Decimal = Decimal("0")


class ReplaceWalletCommandHandler(UpdateExistingWalletCommandHandler):
    # Narrowing the parameter type is a Liskov violation, and a real one: this
    # handler is NOT substitutable for its parent. It reuses the parent for the
    # load-mutate-emit machinery only, and nothing dispatches over the two
    # polymorphically. Composition would make that structural rather than
    # asserted; the inheritance predates this note.
    async def handle(self, command: ReplaceWalletCommand) -> tuple[WalletDTO, int]:  # type: ignore[override]
        wallet_aggregate = await self.load_wallet_aggregate(
            wallet_id=command.wallet_id,
            user_id=command.user_id,
        )

        if wallet_aggregate.root.currency_code != command.currency_code:
            raise WalletCurrencyImmutableError(
                current_currency=wallet_aggregate.root.currency_code,
                requested_currency=command.currency_code,
            )

        return await self.update_and_emit(
            wallet_aggregate,
            UpdateExistingWalletCommand(
                user_id=command.user_id,
                user_external_id=command.user_external_id,
                wallet_id=command.wallet_id,
                new_name=command.name,
                category=command.category,
                color=command.color,
                favorite=command.favorite,
                zero_balance=command.zero_balance,
            ),
        )
