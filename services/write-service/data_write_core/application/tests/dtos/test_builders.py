"""DTO builders: wallet_to_dto, transaction_to_dto, transaction_to_plain_dto."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.application.dtos.builders import (
    transaction_to_dto,
    transaction_to_plain_dto,
    wallet_to_dto,
)
from data_write_core.application.dtos.transaction_dto import (
    TransactionDTO,
    TransactionPlainDTO,
)
from data_write_core.application.dtos.wallet_dto import WalletDTO
from data_write_core.domain.entities import TransactionEntity, WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import TransactionData, WalletData


def _wallet_entity(
    wallet_id: str = "11111111-1111-1111-1111-111111111111",
    title: str = "Main",
    currency: str = "USD",
) -> WalletEntity:
    now = datetime(2026, 1, 1, 12)
    return WalletEntity.create(
        id=wallet_id,
        user_id="9",
        data=WalletData(title=title, currency_code=currency),
        created_at=now,
        updated_at=now,
        _event_collector=EventCollector(),
    )


def _txn_entity(
    *,
    wallet_id: UUID,
    amount: Decimal = Decimal("5"),
    cancels: UUID | None = None,
    adjusts: UUID | None = None,
) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 1, 13),
        data=TransactionData(
            source_wallet_id=wallet_id,
            amount=amount,
            cancels_other=cancels,
            adjusts_other=adjusts,
        ),
    )


class WalletToDtoTests(SimpleTestCase):
    def test_balance_defaults_to_zero_when_not_provided(self) -> None:
        # Important guard: None != 0; the builder explicitly coerces.
        dto = wallet_to_dto(_wallet_entity())

        self.assertEqual(dto.balance_amount, Decimal("0"))

    def test_balance_uses_provided_value_when_given(self) -> None:
        dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("123.45"))

        self.assertEqual(dto.balance_amount, Decimal("123.45"))

    def test_negative_balance_is_passed_through(self) -> None:
        # `balance_amount or 0` would silently zero out negatives;
        # pin the `is not None` check instead.
        dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("-50"))

        self.assertEqual(dto.balance_amount, Decimal("-50"))

    def test_zero_balance_is_passed_through_as_zero(self) -> None:
        dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("0"))

        self.assertEqual(dto.balance_amount, Decimal("0"))

    def test_maps_entity_fields_to_dto(self) -> None:
        wallet = _wallet_entity(title="Savings", currency="EUR")

        dto = wallet_to_dto(wallet)

        self.assertIsInstance(dto, WalletDTO)
        self.assertEqual(dto.id, UUID(wallet.unique_id))
        self.assertEqual(dto.user_id, 9)
        self.assertEqual(dto.name, "Savings")
        self.assertEqual(dto.currency, "EUR")
        self.assertEqual(dto.created_at, wallet.created_at)
        self.assertEqual(dto.updated_at, wallet.updated_at)


class TransactionToDtoTests(SimpleTestCase):
    def test_maps_entity_and_inlines_source_wallet_dto(self) -> None:
        wallet = _wallet_entity()
        wallet_dto = wallet_to_dto(wallet, balance_amount=Decimal("100"))
        txn = _txn_entity(wallet_id=UUID(wallet.unique_id), amount=Decimal("12.50"))

        dto = transaction_to_dto(txn, wallet_dto)

        self.assertIsInstance(dto, TransactionDTO)
        self.assertEqual(dto.id, UUID(txn.unique_id))
        self.assertEqual(dto.amount, Decimal("12.50"))
        self.assertEqual(dto.source_wallet, wallet_dto)
        self.assertEqual(dto.currency_code, wallet_dto.currency)
        self.assertEqual(dto.created_at, txn.created_at)
        self.assertIsNone(dto.cancels_other)
        self.assertIsNone(dto.adjusts_other)

    def test_propagates_cancels_other_link(self) -> None:
        wallet = _wallet_entity()
        cancelled_id = uuid4()
        txn = _txn_entity(
            wallet_id=UUID(wallet.unique_id),
            amount=Decimal("-5"),
            cancels=cancelled_id,
        )

        dto = transaction_to_dto(txn, wallet_to_dto(wallet))

        self.assertEqual(dto.cancels_other, cancelled_id)

    def test_propagates_adjusts_other_link(self) -> None:
        wallet = _wallet_entity()
        adjusted_id = uuid4()
        txn = _txn_entity(
            wallet_id=UUID(wallet.unique_id),
            amount=Decimal("3"),
            adjusts=adjusted_id,
        )

        dto = transaction_to_dto(txn, wallet_to_dto(wallet))

        self.assertEqual(dto.adjusts_other, adjusted_id)

    def test_currency_code_taken_from_wallet_dto_not_entity(self) -> None:
        # If the wallet's currency ever drifts from the txn's stored
        # currency, the DTO must mirror the wallet — authoritative source.
        wallet = _wallet_entity(currency="JPY")
        txn = _txn_entity(wallet_id=UUID(wallet.unique_id))

        dto = transaction_to_dto(txn, wallet_to_dto(wallet))

        self.assertEqual(dto.currency_code, "JPY")


class TransactionToPlainDtoTests(SimpleTestCase):
    def test_plain_dto_stores_wallet_id_as_string(self) -> None:
        wallet = _wallet_entity()
        wallet_dto = wallet_to_dto(wallet)
        txn = _txn_entity(wallet_id=UUID(wallet.unique_id), amount=Decimal("7"))

        plain = transaction_to_plain_dto(txn, wallet_dto)

        self.assertIsInstance(plain, TransactionPlainDTO)
        self.assertEqual(plain.source_wallet_id, str(wallet_dto.id))
        self.assertEqual(plain.amount, Decimal("7"))
        self.assertEqual(plain.currency_code, wallet_dto.currency)
