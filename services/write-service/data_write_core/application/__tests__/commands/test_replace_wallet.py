from uuid import UUID

import pytest

from data_write_core.application.commands import (
    ReplaceWalletCommand,
    ReplaceWalletCommandHandler,
)
from data_write_core.domain.exceptions import WalletCurrencyImmutableError

from ..queries.fakes import FakeTransactionRepository, FakeWalletRepository, make_wallet

WALLET_A = "11111111-1111-1111-1111-111111111111"


async def test_replace_rejects_currency_change():
    wallet_repo = FakeWalletRepository([make_wallet(WALLET_A, currency="USD")])
    handler = ReplaceWalletCommandHandler(
        wallet_repository=wallet_repo,
        transaction_repository=FakeTransactionRepository(),
        outbox_repository=object(),
    )

    with pytest.raises(WalletCurrencyImmutableError):
        await handler.handle(
            ReplaceWalletCommand(
                user_id=7,
                user_external_id="user_abc",
                wallet_id=UUID(WALLET_A),
                name="Renamed",
                currency_code="EUR",
            )
        )
