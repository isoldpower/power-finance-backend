"""TransactionMapper.to_domain: builds a TransactionEntity from a raw row dict (ImmuDB)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from django.test import SimpleTestCase

from data_write_core.infrastructure.repositories.mappers.transaction_mapper import (
    TransactionMapper,
)

_ID = "11111111-1111-1111-1111-111111111111"
_WALLET = "22222222-2222-2222-2222-222222222222"


class TransactionMapperTests(SimpleTestCase):
    def test_plain_row_maps_to_entity_with_all_fields_populated(self) -> None:
        row = {
            "id": _ID,
            "user_id": "42",
            "created_at": "2026-05-20T10:30:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "12.50",
            "cancels_other": None,
            "adjusts_other": None,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertEqual(entity.unique_id, _ID)
        self.assertEqual(entity.user_id, "42")
        self.assertEqual(entity.source_wallet_id, UUID(_WALLET))
        self.assertEqual(entity.amount, Decimal("12.50"))
        self.assertIsNone(entity.cancels_other)
        self.assertIsNone(entity.adjusts_other)
        # parse_datetime returns aware datetime when offset is present
        self.assertEqual(entity.created_at.year, 2026)

    def test_cancels_other_string_is_parsed_to_uuid(self) -> None:
        cancelled = "33333333-3333-3333-3333-333333333333"
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "-5",
            "cancels_other": cancelled,
            "adjusts_other": None,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertEqual(entity.cancels_other, UUID(cancelled))
        self.assertIsNone(entity.adjusts_other)

    def test_adjusts_other_string_is_parsed_to_uuid(self) -> None:
        adjusted = "44444444-4444-4444-4444-444444444444"
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "7",
            "cancels_other": None,
            "adjusts_other": adjusted,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertEqual(entity.adjusts_other, UUID(adjusted))
        self.assertIsNone(entity.cancels_other)

    def test_missing_link_keys_default_to_none(self) -> None:
        # row.get(...) tolerates absent keys; reproduce that path.
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "1",
        }

        entity = TransactionMapper.to_domain(row)

        self.assertIsNone(entity.cancels_other)
        self.assertIsNone(entity.adjusts_other)

    def test_from_persistence_does_not_emit_creation_event(self) -> None:
        # Mapping a stored row must not trigger a TransactionCreatedEvent
        # — that would re-publish history every time we read.
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "1",
            "cancels_other": None,
            "adjusts_other": None,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertEqual(entity.event_collector.pull_events(), [])

    def test_amount_string_with_high_precision_preserved(self) -> None:
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-01-01T00:00:00+00:00",
            "source_wallet_id": _WALLET,
            "amount": "0.00000001",
            "cancels_other": None,
            "adjusts_other": None,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertEqual(entity.amount, Decimal("0.00000001"))

    def test_created_at_is_parsed_via_django_parse_datetime(self) -> None:
        row = {
            "id": _ID,
            "user_id": "1",
            "created_at": "2026-05-20T10:30:45+00:00",
            "source_wallet_id": _WALLET,
            "amount": "1",
            "cancels_other": None,
            "adjusts_other": None,
        }

        entity = TransactionMapper.to_domain(row)

        self.assertIsInstance(entity.created_at, datetime)
        self.assertEqual(entity.created_at.minute, 30)
        self.assertEqual(entity.created_at.second, 45)
