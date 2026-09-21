from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from data_write_core.domain.entities import InternalUserEntity, WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import Currency
from data_write_core.infrastructure.repositories.mappers.currency_mapper import (
    CurrencyMapper,
)
from data_write_core.infrastructure.repositories.mappers.user_mapper import UserMapper
from data_write_core.infrastructure.repositories.mappers.wallet_mapper import (
    WalletMapper,
)


class WalletMapperToDomainTests(SimpleTestCase):
    def _model(self, **overrides) -> SimpleNamespace:
        defaults = {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Main",
            "currency_id": "USD",
            "user_id": 9,
            "created_at": datetime(2026, 1, 1, 12),
            "updated_at": datetime(2026, 1, 2, 12),
            "deleted_at": None,
            "category": "Savings",
            "color": "#FF0000",
            "favorite": False,
            "zero_balance": Decimal("0"),
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_maps_all_fields_to_wallet_entity(self) -> None:
        entity = WalletMapper.to_domain(self._model())

        self.assertIsInstance(entity, WalletEntity)
        self.assertEqual(entity.unique_id, "11111111-1111-1111-1111-111111111111")
        self.assertEqual(entity.title, "Main")
        self.assertEqual(entity.currency_code, "USD")
        self.assertEqual(entity.user_id, "9")
        self.assertEqual(entity.created_at, datetime(2026, 1, 1, 12))
        self.assertEqual(entity.updated_at, datetime(2026, 1, 2, 12))
        self.assertIsNone(entity.deleted_at)

    def test_user_id_is_converted_to_string(self) -> None:
        entity = WalletMapper.to_domain(self._model(user_id=7))

        self.assertEqual(entity.user_id, "7")

    def test_id_is_coerced_to_string_even_when_uuid_typed(self) -> None:
        from uuid import UUID

        uuid_obj = UUID("11111111-1111-1111-1111-111111111111")
        entity = WalletMapper.to_domain(self._model(id=uuid_obj))

        self.assertEqual(entity.unique_id, str(uuid_obj))

    def test_deleted_at_is_propagated(self) -> None:
        deleted_at = datetime(2026, 1, 3)
        entity = WalletMapper.to_domain(self._model(deleted_at=deleted_at))

        self.assertEqual(entity.deleted_at, deleted_at)

    def test_default_event_collector_is_fresh_per_call(self) -> None:
        a = WalletMapper.to_domain(self._model())
        b = WalletMapper.to_domain(self._model())

        self.assertIsInstance(a.event_collector, EventCollector)
        self.assertIsNot(a.event_collector, b.event_collector)


class WalletMapperApplyToModelTests(SimpleTestCase):
    def _entity(self, **overrides) -> WalletEntity:
        defaults = {
            "id": "11111111-1111-1111-1111-111111111111",
            "title": "Main",
            "currency_code": "USD",
            "user_id": "9",
            "created_at": datetime(2026, 1, 1, 12),
            "updated_at": datetime(2026, 1, 2, 12),
            "deleted_at": None,
            "category": "Savings",
            "color": "#FF0000",
            "favorite": False,
            "zero_balance": Decimal("0"),
        }
        defaults.update(overrides)
        return WalletEntity(
            event_collector=EventCollector(),
            **defaults,
        )

    def test_apply_writes_entity_state_back_to_model(self) -> None:
        model = SimpleNamespace(
            id=None, name="stale", currency_id="x", user_id=None, deleted_at=datetime(2026, 1, 1)
        )

        returned = WalletMapper.apply_to_model(model, self._entity(title="New", deleted_at=None))

        self.assertIs(returned, model)
        self.assertEqual(model.name, "New")
        self.assertEqual(model.currency_id, "USD")
        self.assertEqual(model.user_id, 9)
        self.assertIsNone(model.deleted_at)

    def test_apply_writes_deleted_at_unconditionally(self) -> None:
        model = SimpleNamespace(id=None, name="x", currency_id="x", user_id=None, deleted_at=None)
        entity = self._entity(deleted_at=datetime(2026, 3, 1))

        WalletMapper.apply_to_model(model, entity)

        self.assertEqual(model.deleted_at, datetime(2026, 3, 1))

    def test_apply_propagates_id_from_entity(self) -> None:
        model = SimpleNamespace(
            id="other", name="x", currency_id="x", user_id=None, deleted_at=None
        )

        WalletMapper.apply_to_model(model, self._entity())

        self.assertEqual(model.id, "11111111-1111-1111-1111-111111111111")


class CurrencyMapperTests(SimpleTestCase):
    def test_to_domain_copies_all_fields(self) -> None:
        model = SimpleNamespace(code="USD", name="US Dollar", numeric="840", digits=2)

        currency = CurrencyMapper.to_domain(model)

        self.assertEqual(
            currency,
            Currency(code="USD", name="US Dollar", numeric="840", digits=2),
        )


class UserMapperTests(SimpleTestCase):
    def test_to_domain_builds_internal_user_entity(self) -> None:
        model = SimpleNamespace(
            id=42,
            username="user_2abc",
            email="user@example.com",
            first_name="A",
            last_name="B",
        )

        entity = UserMapper.to_domain(model)

        self.assertIsInstance(entity, InternalUserEntity)
        self.assertEqual(entity.unique_id, "42")
        self.assertEqual(entity.external_id, "user_2abc")

    def test_id_coerced_to_string(self) -> None:
        model = SimpleNamespace(id=7, username="user_7", email="x@x", first_name="x", last_name="x")

        self.assertEqual(UserMapper.to_domain(model).unique_id, "7")
