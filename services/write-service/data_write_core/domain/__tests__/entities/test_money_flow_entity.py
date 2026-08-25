from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from data_write_core.domain.entities import MoneyFlowEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import MoneyFlowData


def _money_flow_data(
    amount: Decimal = Decimal("10"), wallet_id: UUID | None = None
) -> MoneyFlowData:
    return MoneyFlowData(
        transaction_id=uuid4(),
        container_id=wallet_id or uuid4(),
        amount=amount,
        cancels_other=None,
        adjusts_other=None,
    )


class MoneyFlowCreateTests(SimpleTestCase):
    def test_create_emits_nothing_on_its_own(self) -> None:
        """A flow is not an event-worthy fact by itself. The transaction that
        owns it raises TransactionCreatedEvent, once, for the whole thing."""

        collector = EventCollector()
        MoneyFlowEntity.create(user_id=9, data=_money_flow_data(), _event_collector=collector)

        self.assertEqual(collector.pull_events(), [])

    def test_create_assigns_unique_id_per_call(self) -> None:
        wallet_id = uuid4()
        a = MoneyFlowEntity.create(user_id=1, data=_money_flow_data(wallet_id=wallet_id))
        b = MoneyFlowEntity.create(user_id=1, data=_money_flow_data(wallet_id=wallet_id))

        self.assertNotEqual(a.unique_id, b.unique_id)

    def test_create_falls_back_to_default_collector_when_none_provided(self) -> None:
        money_flow = MoneyFlowEntity.create(user_id=1, data=_money_flow_data())

        self.assertIsInstance(money_flow.event_collector, EventCollector)

    def test_create_stores_user_id_as_a_string(self) -> None:
        flow = MoneyFlowEntity.create(user_id=42, data=_money_flow_data())

        self.assertEqual(flow.user_id, "42")


class MoneyFlowFromPersistenceTests(SimpleTestCase):
    def test_from_persistence_does_not_emit_creation_event(self) -> None:
        collector = EventCollector()

        MoneyFlowEntity.from_persistence(
            id=uuid4(),
            user_id=1,
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            data=_money_flow_data(),
            _event_collector=collector,
        )

        self.assertEqual(collector.pull_events(), [])

    def test_from_persistence_round_trips_all_data(self) -> None:
        txn_id = uuid4()
        wallet_id = uuid4()
        created_at = datetime(2026, 5, 20, 10, 30, 0)

        money_flow = MoneyFlowEntity.from_persistence(
            id=txn_id,
            user_id=7,
            created_at=created_at,
            data=MoneyFlowData(
                transaction_id=uuid4(),
                container_id=wallet_id,
                amount=Decimal("12.50"),
                cancels_other=None,
                adjusts_other=None,
            ),
        )

        self.assertEqual(money_flow.unique_id, str(txn_id))
        self.assertEqual(money_flow.user_id, "7")
        self.assertEqual(money_flow.created_at, created_at)
        self.assertEqual(money_flow.container_id, wallet_id)
        self.assertEqual(money_flow.amount, Decimal("12.50"))


class MoneyFlowInverseTests(SimpleTestCase):
    def test_create_inverse_negates_amount(self) -> None:
        original = MoneyFlowEntity.create(user_id=1, data=_money_flow_data(amount=Decimal("15")))
        original.event_collector.pull_events()

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.amount, Decimal("-15"))

    def test_create_inverse_links_back_via_cancels_other(self) -> None:
        original = MoneyFlowEntity.create(user_id=1, data=_money_flow_data())

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.cancels_other, UUID(original.unique_id))
        self.assertIsNone(inverse.adjusts_other)

    def test_create_inverse_preserves_source_wallet_and_user(self) -> None:
        wallet_id = uuid4()
        original = MoneyFlowEntity.create(
            user_id=88, data=_money_flow_data(amount=Decimal("3"), wallet_id=wallet_id)
        )

        inverse = original.create_inverse(event_collector=EventCollector())

        self.assertEqual(inverse.container_id, wallet_id)
        self.assertEqual(inverse.user_id, "88")

    def test_create_inverse_emits_nothing(self) -> None:
        collector = EventCollector()
        original = MoneyFlowEntity.create(user_id=9, data=_money_flow_data())

        original.create_inverse(event_collector=collector)

        self.assertEqual(collector.pull_events(), [])
