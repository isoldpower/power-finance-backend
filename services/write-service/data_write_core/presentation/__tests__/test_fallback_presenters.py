"""The fallback presenters must produce what the read service produces.

The gateway can reroute a read here mid-session; a client that could tell the
difference would be watching the consistency mechanism leak.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest

from data_write_core.application.dtos import TransactionPlainDTO, WalletDTO
from data_write_core.presentation.http.views.fallback_read._presenters import (
    present_transaction,
    present_wallet,
)

WALLET_ID = UUID("11111111-1111-1111-1111-111111111111")
TX_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

SCALES = {"USD": 2, "EUR": 2, "JPY": 0}


@pytest.fixture(autouse=True)
def _static_currency_scales():
    with patch(
        "data_write_core.application.money_scales.load_scales",
        return_value=SCALES,
    ):
        yield


async def test_present_wallet_matches_read_service_shape():
    wallet = WalletDTO(
        id=WALLET_ID,
        user_id=7,
        name="Vacation",
        balance_amount=Decimal("130.00"),
        currency="USD",
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 1, 2, 12, 0, 0),
    )

    assert await present_wallet(wallet) == {
        "id": str(WALLET_ID),
        "name": "Vacation",
        "balance": {"amount": "130.00", "currency": "USD"},
        "created_at": "2026-01-01T12:00:00+00:00",
        "updated_at": "2026-01-02T12:00:00+00:00",
        "deleted_at": None,
    }


async def test_present_transaction_matches_read_service_shape():
    transaction = TransactionPlainDTO(
        id=TX_ID,
        amount=Decimal("12.50"),
        currency_code="EUR",
        source_wallet_id=str(WALLET_ID),
        created_at=datetime(2026, 1, 1, 9, 30, 0),
    )

    assert await present_transaction(transaction) == {
        "id": str(TX_ID),
        "wallet_id": str(WALLET_ID),
        "amount": "12.50",
        "currency": "EUR",
        "occurred_at": "2026-01-01T09:30:00+00:00",
        "created_at": "2026-01-01T09:30:00+00:00",
        "updated_at": None,
        "deleted_at": None,
    }


async def test_amounts_are_emitted_at_the_currency_scale():
    """Same code path, different scale: two digits for USD, none for JPY."""

    transaction = TransactionPlainDTO(
        id=TX_ID,
        amount=Decimal("90"),
        currency_code="JPY",
        source_wallet_id=str(WALLET_ID),
        created_at=datetime(2026, 1, 1, 9, 30, 0),
    )

    presented = await present_transaction(transaction)

    assert presented["amount"] == "90"
