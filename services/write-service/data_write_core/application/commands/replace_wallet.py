from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.exceptions import WalletCurrencyImmutableError

from ..dtos import WalletDTO
from .update_existing_wallet import (
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)


@dataclass(frozen=True)
class ReplaceWalletCommand:
    """Full PUT-style replacement of a wallet's representation. Only the name
    is replaceable; the sent currency must match the wallet's denomination."""

    user_id: int
    user_external_id: str
    wallet_id: UUID
    name: str
    currency_code: str


class ReplaceWalletCommandHandler(UpdateExistingWalletCommandHandler):
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

        return await self.rename_and_emit(
            wallet_aggregate,
            UpdateExistingWalletCommand(
                user_id=command.user_id,
                user_external_id=command.user_external_id,
                wallet_id=command.wallet_id,
                new_name=command.name,
            ),
        )
