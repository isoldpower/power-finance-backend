"""Small entities: BalanceCheckpoint, Currency, InternalUser. Mostly identity wiring."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.test import SimpleTestCase

from data_write_core.domain.entities import (
    BalanceCheckpointEntity,
    CurrencyEntity,
    InternalUserEntity,
)
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import Currency


class BalanceCheckpointEntityTests(SimpleTestCase):
    def test_exposes_balance_and_created_at(self) -> None:
        created_at = datetime(2026, 1, 1, 0, 0, 0)

        checkpoint = BalanceCheckpointEntity(
            id="ckpt-1",
            created_at=created_at,
            balance=Decimal("123.45"),
        )

        self.assertEqual(checkpoint.unique_id, "ckpt-1")
        self.assertEqual(checkpoint.balance, Decimal("123.45"))
        self.assertEqual(checkpoint.created_at, created_at)

    def test_provides_default_event_collector_when_none_given(self) -> None:
        checkpoint = BalanceCheckpointEntity(
            id="ckpt-1",
            created_at=datetime(2026, 1, 1),
            balance=Decimal("0"),
        )

        self.assertIsInstance(checkpoint.event_collector, EventCollector)


class CurrencyEntityTests(SimpleTestCase):
    def test_unique_id_equals_currency_code(self) -> None:
        entity = CurrencyEntity(
            currency_data=Currency(code="USD", name="US Dollar", numeric="840", digits=2)
        )

        self.assertEqual(entity.unique_id, "USD")

    def test_accepts_external_collector(self) -> None:
        collector = EventCollector()
        entity = CurrencyEntity(
            currency_data=Currency(code="EUR", name="Euro", numeric="978", digits=2),
            collector=collector,
        )

        self.assertIs(entity.event_collector, collector)


class InternalUserEntityTests(SimpleTestCase):
    def test_unique_id_is_provided_user_id(self) -> None:
        user = InternalUserEntity(
            user_id="42",
            external_id="user_2abc",
            email="user@example.com",
            first_name="A",
            last_name="B",
        )

        self.assertEqual(user.unique_id, "42")

    def test_default_collector_is_independent_per_instance(self) -> None:
        a = InternalUserEntity(
            user_id="1", external_id="user_a", email="a@x", first_name="A", last_name="A"
        )
        b = InternalUserEntity(
            user_id="2", external_id="user_b", email="b@x", first_name="B", last_name="B"
        )

        self.assertIsNot(a.event_collector, b.event_collector)
