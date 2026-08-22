from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest

from data_write_core.application.dtos import TransactionDTO, WalletDTO
from data_write_core.domain.value_objects import TransactionOrigin, TransactionType
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
        category="Savings",
        color="#FF0000",
        favorite=True,
        zero_balance=Decimal("100.00"),
    )

    assert await present_wallet(wallet) == {
        "id": str(WALLET_ID),
        "name": "Vacation",
        "created_at": "2026-01-01T12:00:00+00:00",
        "updated_at": "2026-01-02T12:00:00+00:00",
        "deleted_at": None,
        "category": "Savings",
        "currency": "USD",
        "money": {"amount": "130.00", "currency": "USD"},
        "zero_balance": {"amount": "100.00", "currency": "USD"},
        "favorite": True,
        "color": "#FF0000",
    }


def _transaction(amount: str, currency: str = "EUR") -> TransactionDTO:
    return TransactionDTO(
        id=TX_ID,
        user_id=7,
        name="Groceries store",
        amount=Decimal(amount),
        currency_code=currency,
        transaction_type=TransactionType.EXPENSE,
        origin=TransactionOrigin.MANUAL,
        wallet=WalletDTO(
            id=WALLET_ID,
            user_id=7,
            name="Random Credit Card",
            balance_amount=Decimal("0"),
            currency=currency,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            updated_at=datetime(2026, 1, 1, 12, 0, 0),
        ),
        created_at=datetime(2026, 1, 1, 9, 30, 0),
        category="Food",
    )


async def test_present_transaction_matches_read_service_shape():
    assert await present_transaction(_transaction("12.50")) == {
        "id": str(TX_ID),
        "name": "Groceries store",
        "created_at": "2026-01-01T09:30:00+00:00",
        "updated_at": None,
        "deleted_at": None,
        "money": {"amount": "12.50", "currency": "EUR"},
        "type": "expense",
        "origin": "manual",
        "wallet": {"id": str(WALLET_ID), "name": "Random Credit Card"},
        "category": "Food",
        "chain_id": None,
    }


async def test_amounts_are_emitted_at_the_currency_scale():
    """Same code path, different scale: two digits for EUR, none for JPY."""

    presented = await present_transaction(_transaction("90", currency="JPY"))

    assert presented["money"] == {"amount": "90", "currency": "JPY"}
