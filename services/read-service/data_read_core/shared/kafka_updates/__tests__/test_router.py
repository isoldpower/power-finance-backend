"""KafkaEventRouter — registration and dispatch."""

import pytest

from data_read_core.shared.kafka_updates import EventMessage, KafkaEventRouter
from data_read_core.shared.kafka_updates.exceptions import HandlerNotFoundError


def _event(event_type: str = "WalletCreated") -> EventMessage:
    return EventMessage(
        event_id="e1",
        event_type=event_type,
        aggregate_type="wallet",
        aggregate_id="w1",
        outbox_seq=1,
        payload=b"{}",
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )


def test_has_and_registered_event_types():
    router = KafkaEventRouter()
    assert not router.has("WalletCreated")

    router.register("WalletCreated", lambda event: None)

    assert router.has("WalletCreated")
    assert router.registered_event_types() == ["WalletCreated"]


async def test_dispatch_runs_all_handlers_in_registration_order():
    router = KafkaEventRouter()
    calls: list[str] = []

    async def first(event):
        calls.append("first")

    async def second(event):
        calls.append("second")

    router.register("WalletCreated", first)
    router.register("WalletCreated", second)

    await router.dispatch(_event())

    assert calls == ["first", "second"]


async def test_dispatch_unknown_event_raises():
    with pytest.raises(HandlerNotFoundError, match="WalletCreated"):
        await KafkaEventRouter().dispatch(_event())
