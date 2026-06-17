"""DomainEvent base: every event auto-stamps event_id and occurred_at."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from django.test import SimpleTestCase

from data_write_core.domain.events import DomainEvent


@dataclass(frozen=True)
class _Sample(DomainEvent):
    payload: str = ""


class DomainEventEnvelopeTests(SimpleTestCase):
    def test_event_id_is_a_uuid(self) -> None:
        event = _Sample(payload="x")

        self.assertIsInstance(event.event_id, UUID)

    def test_event_id_is_unique_per_instance(self) -> None:
        a = _Sample()
        b = _Sample()

        self.assertNotEqual(a.event_id, b.event_id)

    def test_occurred_at_is_timezone_aware_utc(self) -> None:
        event = _Sample()

        self.assertEqual(event.occurred_at.tzinfo, UTC)

    def test_occurred_at_is_set_at_construction_time(self) -> None:
        before = datetime.now(UTC)
        event = _Sample()
        after = datetime.now(UTC)

        self.assertLessEqual(before, event.occurred_at)
        self.assertLessEqual(event.occurred_at, after)

    def test_event_is_frozen(self) -> None:
        event = _Sample(payload="x")

        with self.assertRaises(Exception):
            event.payload = "tampered"  # type: ignore[misc]
