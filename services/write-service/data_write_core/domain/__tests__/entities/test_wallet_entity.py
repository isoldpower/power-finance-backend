"""WalletEntity: lifecycle (rename, soft-delete, restore) and event-collector wiring."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.test import SimpleTestCase

from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import WalletData


def _make_wallet(
    *,
    title: str = "Main",
    currency: str = "USD",
    deleted_at: datetime | None = None,
    collector: EventCollector | None = None,
) -> WalletEntity:
    now = datetime(2026, 1, 1, 12, 0, 0)
    return WalletEntity.create(
        id="11111111-1111-1111-1111-111111111111",
        user_id="7",
        data=WalletData(title=title, currency_code=currency),
        created_at=now,
        updated_at=now,
        deleted_at=deleted_at,
        _event_collector=collector,
    )


class WalletEntityFactoryTests(SimpleTestCase):
    def test_create_assigns_provided_collector(self) -> None:
        collector = EventCollector()
        wallet = _make_wallet(collector=collector)

        self.assertIs(wallet.event_collector, collector)

    def test_create_provides_default_collector_when_none_given(self) -> None:
        wallet = _make_wallet()

        self.assertIsInstance(wallet.event_collector, EventCollector)

    def test_created_at_and_updated_at_initially_equal(self) -> None:
        wallet = _make_wallet()

        self.assertEqual(wallet.created_at, wallet.updated_at)

    def test_deleted_at_defaults_to_none_when_not_provided(self) -> None:
        self.assertIsNone(_make_wallet().deleted_at)


class WalletEntityMutationTests(SimpleTestCase):
    def test_rename_updates_title_and_updated_at(self) -> None:
        wallet = _make_wallet(title="Old")
        new_now = wallet.updated_at + timedelta(hours=1)

        wallet.rename("New", new_now)

        self.assertEqual(wallet.title, "New")
        self.assertEqual(wallet.updated_at, new_now)

    def test_rename_does_not_touch_created_at(self) -> None:
        wallet = _make_wallet()
        original_created = wallet.created_at

        wallet.rename("Renamed", wallet.updated_at + timedelta(hours=1))

        self.assertEqual(wallet.created_at, original_created)

    def test_mark_deleted_sets_deleted_at_and_updated_at(self) -> None:
        wallet = _make_wallet()
        delete_time = wallet.updated_at + timedelta(days=1)

        wallet.mark_deleted(delete_time)

        self.assertEqual(wallet.deleted_at, delete_time)
        self.assertEqual(wallet.updated_at, delete_time)

    def test_restore_clears_deleted_at_and_updates_timestamp(self) -> None:
        wallet = _make_wallet(deleted_at=datetime(2026, 1, 2, 0, 0, 0))
        restored_at = datetime(2026, 1, 3, 0, 0, 0)

        wallet.restore(restored_at)

        self.assertIsNone(wallet.deleted_at)
        self.assertEqual(wallet.updated_at, restored_at)

    def test_restore_emits_no_events(self) -> None:
        collector = EventCollector()
        wallet = _make_wallet(deleted_at=datetime(2026, 1, 2), collector=collector)

        wallet.restore(datetime(2026, 1, 3))

        self.assertEqual(collector.pull_events(), [])

    def test_mark_deleted_emits_no_events_directly(self) -> None:
        collector = EventCollector()
        wallet = _make_wallet(collector=collector)

        wallet.mark_deleted(datetime(2026, 1, 2))

        self.assertEqual(collector.pull_events(), [])
