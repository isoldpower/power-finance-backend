"""RoutedMessageProcessor — decode, route, or divert to the malformed DLQ."""

from fakes import make_consumed_message

from data_read_core.shared.kafka_updates import EventMessage, RoutedMessageProcessor
from data_read_core.shared.kafka_updates.exceptions import MalformedEnvelope


def _event(event_type="WalletCreated") -> EventMessage:
    return EventMessage(
        event_id="e1",
        event_type=event_type,
        aggregate_type="wallet",
        partition_key="w1",
        outbox_seq=1,
        payload=b"{}",
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )


class _FakeDecoder:
    def __init__(self, *, event=None, error=None):
        self._event = event
        self._error = error

    def decode(self, message):
        if self._error is not None:
            raise self._error
        return self._event

    def extract_event_id(self, message):
        return "e1"


class _FakeRouter:
    def __init__(self, *, known: bool):
        self._known = known
        self.dispatched: list[EventMessage] = []

    def has(self, event_type: str) -> bool:
        return self._known

    async def dispatch(self, event: EventMessage) -> None:
        self.dispatched.append(event)


class _FakeDLQ:
    def __init__(self):
        self.published: list[dict] = []

    async def publish(self, message, *, error, total_attempts):
        self.published.append(
            {"message": message, "error": error, "total_attempts": total_attempts}
        )


async def test_dispatches_when_handler_registered():
    event = _event()
    router = _FakeRouter(known=True)
    dlq = _FakeDLQ()
    processor = RoutedMessageProcessor(_FakeDecoder(event=event), router, dlq)

    await processor(make_consumed_message())

    assert router.dispatched == [event]
    assert dlq.published == []


async def test_unknown_event_type_is_dropped_not_dispatched():
    router = _FakeRouter(known=False)
    dlq = _FakeDLQ()
    processor = RoutedMessageProcessor(_FakeDecoder(event=_event("Unhandled")), router, dlq)

    await processor(make_consumed_message())

    assert router.dispatched == []
    assert dlq.published == []


async def test_malformed_envelope_routes_to_dlq_without_dispatch():
    router = _FakeRouter(known=True)
    dlq = _FakeDLQ()
    error = MalformedEnvelope("missing headers")
    processor = RoutedMessageProcessor(_FakeDecoder(error=error), router, dlq)

    message = make_consumed_message()
    await processor(message)

    assert router.dispatched == []
    assert len(dlq.published) == 1
    assert dlq.published[0]["message"] is message
    assert dlq.published[0]["error"] is error
    assert dlq.published[0]["total_attempts"] == 1
