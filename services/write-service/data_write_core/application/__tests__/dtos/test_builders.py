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
from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import MoneyFlowEntity, TransactionEntity, WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import (
    MoneyFlowData,
    TransactionMetadata,
    WalletData,
)


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
) -> MoneyFlowEntity:
    return MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=9,
        created_at=datetime(2026, 1, 1, 13),
        data=MoneyFlowData(
            transaction_id=uuid4(),
            source_wallet_id=wallet_id,
            amount=amount,
            cancels_other=cancels,
            adjusts_other=adjusts,
        ),
    )


class WalletToDtoTests(SimpleTestCase):
    def test_balance_defaults_to_zero_when_not_provided(self) -> None:
        built_dto = wallet_to_dto(_wallet_entity())

        self.assertEqual(built_dto.balance_amount, Decimal("0"))

    def test_balance_uses_provided_value_when_given(self) -> None:
        built_dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("123.45"))

        self.assertEqual(built_dto.balance_amount, Decimal("123.45"))

    def test_negative_balance_is_passed_through(self) -> None:
        built_dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("-50"))

        self.assertEqual(built_dto.balance_amount, Decimal("-50"))

    def test_zero_balance_is_passed_through_as_zero(self) -> None:
        built_dto = wallet_to_dto(_wallet_entity(), balance_amount=Decimal("0"))

        self.assertEqual(built_dto.balance_amount, Decimal("0"))

    def test_maps_entity_fields_to_dto(self) -> None:
        wallet = _wallet_entity(title="Savings", currency="EUR")

        built_dto = wallet_to_dto(wallet)

        self.assertIsInstance(built_dto, WalletDTO)
        self.assertEqual(built_dto.id, UUID(wallet.unique_id))
        self.assertEqual(built_dto.user_id, 9)
        self.assertEqual(built_dto.name, "Savings")
        self.assertEqual(built_dto.currency, "EUR")
        self.assertEqual(built_dto.created_at, wallet.created_at)
        self.assertEqual(built_dto.updated_at, wallet.updated_at)


class TransactionToDtoTests(SimpleTestCase):
    @staticmethod
    def _aggregate(wallet_id: UUID, *amounts: str) -> TransactionAggregate:
        transaction = TransactionEntity(
            id=uuid4(),
            user_id="9",
            wallet_id=wallet_id,
            metadata=TransactionMetadata(name="Groceries", category="Food"),
            created_at=datetime(2026, 1, 1),
            event_collector=EventCollector(),
        )
        flows = [
            MoneyFlowEntity.from_persistence(
                id=uuid4(),
                user_id=9,
                created_at=datetime(2026, 1, 1),
                data=MoneyFlowData(
                    transaction_id=UUID(transaction.unique_id),
                    source_wallet_id=wallet_id,
                    amount=Decimal(amount),
                ),
            )
            for amount in amounts
        ]

        return TransactionAggregate(transaction_entity=transaction, flows=flows)

    def test_maps_the_aggregate_and_inlines_the_wallet(self) -> None:
        wallet = _wallet_entity()
        wallet_dto = wallet_to_dto(wallet, balance_amount=Decimal("100"))
        aggregate = self._aggregate(UUID(wallet.unique_id), "-12.50")

        built_dto = transaction_to_dto(aggregate, wallet_dto)

        self.assertIsInstance(built_dto, TransactionDTO)
        self.assertEqual(built_dto.id, UUID(aggregate.unique_id))
        self.assertEqual(built_dto.wallet, wallet_dto)
        self.assertEqual(built_dto.currency_code, wallet_dto.currency)
        self.assertEqual(built_dto.name, "Groceries")
        self.assertEqual(built_dto.category, "Food")
        self.assertIsNone(built_dto.chain_id)

    def test_amount_leaves_as_a_positive_magnitude(self) -> None:
        """Direction is carried by `type`, so the sign never reaches the wire."""

        wallet = _wallet_entity()
        aggregate = self._aggregate(UUID(wallet.unique_id), "-12.50")

        built_dto = transaction_to_dto(aggregate, wallet_to_dto(wallet))

        self.assertEqual(built_dto.amount, Decimal("12.50"))
        self.assertEqual(str(built_dto.transaction_type), "expense")

    def test_income_keeps_its_sign_out_of_the_amount_too(self) -> None:
        wallet = _wallet_entity()
        aggregate = self._aggregate(UUID(wallet.unique_id), "40")

        built_dto = transaction_to_dto(aggregate, wallet_to_dto(wallet))

        self.assertEqual(built_dto.amount, Decimal("40"))
        self.assertEqual(str(built_dto.transaction_type), "income")

    def test_the_amount_is_the_fold_of_every_flow(self) -> None:
        wallet = _wallet_entity()
        aggregate = self._aggregate(UUID(wallet.unique_id), "-50", "-20")

        built_dto = transaction_to_dto(aggregate, wallet_to_dto(wallet))

        self.assertEqual(built_dto.amount, Decimal("70"))

    def test_currency_code_taken_from_wallet_dto_not_entity(self) -> None:
        wallet = _wallet_entity(currency="JPY")
        aggregate = self._aggregate(UUID(wallet.unique_id), "-10")

        built_dto = transaction_to_dto(aggregate, wallet_to_dto(wallet))

        self.assertEqual(built_dto.currency_code, "JPY")


class TransactionToPlainDtoTests(SimpleTestCase):
    def test_plain_dto_stores_wallet_id_as_string(self) -> None:
        wallet = _wallet_entity()
        wallet_dto = wallet_to_dto(wallet)
        transaction = _txn_entity(wallet_id=UUID(wallet.unique_id), amount=Decimal("7"))

        plain = transaction_to_plain_dto(transaction, wallet_dto)

        self.assertIsInstance(plain, TransactionPlainDTO)
        self.assertEqual(plain.source_wallet_id, str(wallet_dto.id))
        self.assertEqual(plain.amount, Decimal("7"))
        self.assertEqual(plain.currency_code, wallet_dto.currency)
