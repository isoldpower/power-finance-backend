"""InMemoryEventBus: subscribers receive only events of their subscribed type."""

from __future__ import annotations

from dataclasses import dataclass
from unittest import IsolatedAsyncioTestCase

from data_write_core.domain.events import DomainEvent
from data_write_core.infrastructure.messaging.memory_event_bus import InMemoryEventBus


@dataclass(frozen=True)
class _AlphaEvent(DomainEvent):
    payload: str = ""


@dataclass(frozen=True)
class _BetaEvent(DomainEvent):
    payload: str = ""


class InMemoryEventBusTests(IsolatedAsyncioTestCase):
    async def test_publish_with_no_subscribers_is_a_silent_noop(self) -> None:
        bus = InMemoryEventBus()

        await bus.publish([_AlphaEvent(payload="x")])

    async def test_handler_receives_event_of_its_subscribed_type(self) -> None:
        bus = InMemoryEventBus()
        received: list[_AlphaEvent] = []

        async def handler(event: _AlphaEvent) -> None:
            received.append(event)

        bus.subscribe(_AlphaEvent, handler)
        event = _AlphaEvent(payload="hello")
        await bus.publish([event])

        self.assertEqual(received, [event])

    async def test_handler_does_not_receive_other_event_types(self) -> None:
        bus = InMemoryEventBus()
        received: list[_AlphaEvent] = []

        async def alpha_handler(event: _AlphaEvent) -> None:
            received.append(event)

        bus.subscribe(_AlphaEvent, alpha_handler)
        await bus.publish([_BetaEvent(payload="ignore me")])

        self.assertEqual(received, [])

    async def test_multiple_handlers_for_same_type_all_fire_in_registration_order(self) -> None:
        bus = InMemoryEventBus()
        order: list[str] = []

        async def first(event: _AlphaEvent) -> None:
            order.append("first")

        async def second(event: _AlphaEvent) -> None:
            order.append("second")

        bus.subscribe(_AlphaEvent, first)
        bus.subscribe(_AlphaEvent, second)
        await bus.publish([_AlphaEvent(payload="x")])

        self.assertEqual(order, ["first", "second"])

    async def test_publishing_batch_dispatches_events_one_at_a_time_in_order(self) -> None:
        bus = InMemoryEventBus()
        seen: list[str] = []

        async def handler(event: _AlphaEvent) -> None:
            seen.append(event.payload)

        bus.subscribe(_AlphaEvent, handler)
        await bus.publish(
            [_AlphaEvent(payload="a"), _AlphaEvent(payload="b"), _AlphaEvent(payload="c")]
        )

        self.assertEqual(seen, ["a", "b", "c"])

    async def test_handler_exception_propagates_and_halts_remaining_dispatch(self) -> None:
        bus = InMemoryEventBus()
        seen: list[str] = []

        async def explode(event: _AlphaEvent) -> None:
            raise RuntimeError("boom")

        async def collect(event: _AlphaEvent) -> None:
            seen.append(event.payload)

        bus.subscribe(_AlphaEvent, collect)
        bus.subscribe(_AlphaEvent, explode)

        with self.assertRaises(RuntimeError):
            await bus.publish([_AlphaEvent(payload="a"), _AlphaEvent(payload="b")])

        self.assertEqual(seen, ["a"])
