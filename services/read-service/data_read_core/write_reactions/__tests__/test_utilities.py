"""Shared write-reaction helpers: payload decoding and DB-error swallowing."""

import pytest
from django.db import DataError, IntegrityError
from fakes import make_event
from kafka_client_py import PoisonError
from kafka_messages import WalletCreated

from data_read_core.shared.kafka_updates import EventMessage
from data_read_core.write_reactions._utilities import decode_payload, handle_database_errors


def test_decode_payload_parses_known_message():
    event = make_event(WalletCreated(wallet_id="w1", user_id=7, title="Main"))

    payload = decode_payload(event, WalletCreated)

    assert payload.wallet_id == "w1"
    assert payload.title == "Main"


def test_decode_payload_raises_poison_on_garbage_body():
    event = EventMessage(
        event_id="evt-bad",
        event_type="WalletCreated",
        aggregate_type="wallet",
        aggregate_id="w1",
        outbox_seq=1,
        payload=b"not-json",
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )

    with pytest.raises(PoisonError):
        decode_payload(event, WalletCreated)


@pytest.mark.django_db(transaction=True)
async def test_handle_database_errors_returns_effect_result():
    async def _effect(payload):
        return f"ok:{payload}"

    result = await handle_database_errors(_effect, "payload", resource_id="r1")

    assert result == "ok:payload"


@pytest.mark.django_db(transaction=True)
async def test_handle_database_errors_swallows_integrity_error():
    async def _effect(_payload):
        raise IntegrityError("duplicate key")

    result = await handle_database_errors(_effect, None, resource_id="r1")

    assert result is None  # swallowed, not raised


@pytest.mark.django_db(transaction=True)
async def test_handle_database_errors_swallows_data_error():
    async def _effect(_payload):
        raise DataError("value too long")

    result = await handle_database_errors(_effect, None, resource_id="r1")

    assert result is None
