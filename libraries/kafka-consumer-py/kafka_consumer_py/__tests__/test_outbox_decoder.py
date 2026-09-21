"""OutboxEnvelopeDecoder — ConsumedMessage -> EventMessage."""

import pytest

from kafka_consumer_py import OutboxEnvelopeDecoder
from kafka_consumer_py.exceptions import MalformedEnvelope
from kafka_consumer_py.fakes import FakeConsumedMessage, make_consumed_message


def test_decode_maps_headers_key_and_metadata():
    message = make_consumed_message(
        event_id="evt-9",
        event_type="WalletCreated",
        aggregate_type="wallet",
        outbox_seq=42,
        key=b"w1",
        value=b'{"wallet_id": "w1"}',
        topic="events.async",
        partition=3,
        offset=100,
    )

    event = OutboxEnvelopeDecoder().decode(message)

    assert event.event_id == "evt-9"
    assert event.event_type == "WalletCreated"
    assert event.aggregate_type == "wallet"
    assert event.partition_key == "w1"
    assert event.outbox_seq == 42
    assert event.payload == b'{"wallet_id": "w1"}'
    assert (event.topic, event.partition, event.offset) == ("events.async", 3, 100)


def test_decode_missing_event_id_is_malformed():
    with pytest.raises(MalformedEnvelope):
        OutboxEnvelopeDecoder().decode(make_consumed_message(event_id=None))


def test_decode_missing_event_type_is_malformed():
    with pytest.raises(MalformedEnvelope):
        OutboxEnvelopeDecoder().decode(make_consumed_message(event_type=None))


def test_decode_absent_outbox_seq_becomes_none():
    event = OutboxEnvelopeDecoder().decode(make_consumed_message(outbox_seq=None))
    assert event.outbox_seq is None


def test_decode_absent_key_yields_empty_partition_key():
    event = OutboxEnvelopeDecoder().decode(make_consumed_message(key=None))
    assert event.partition_key == ""


def test_decode_absent_value_yields_empty_payload():
    message = make_consumed_message(value=None)
    event = OutboxEnvelopeDecoder().decode(message)
    assert event.payload == b""


def test_extract_event_id_helper():
    decoder = OutboxEnvelopeDecoder()
    assert decoder.extract_event_id(make_consumed_message(event_id="evt-1")) == "evt-1"
    assert decoder.extract_event_id(FakeConsumedMessage(headers=[])) is None
