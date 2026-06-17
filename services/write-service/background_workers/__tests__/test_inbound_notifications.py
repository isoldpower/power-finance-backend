import json
from dataclasses import dataclass

import pytest
from kafka_client_py import PoisonError

from background_workers.services.inbound_notifications import _parse_notification_request


@dataclass
class FakeRecord:
    value: bytes | None
    topic: str = "notifications.inbound"
    partition: int = 0
    offset: int = 0
    key: bytes | None = None
    headers: tuple = ()


def test_parse_valid_notification_request():
    record = FakeRecord(
        value=json.dumps(
            {
                "event_id": "e-1",
                "user_id": 7,
                "user_external_id": "user_abc",
                "short": "Webhook delivered",
                "message": "Delivery to https://example.com succeeded",
                "payload": {"delivery_id": "d-1"},
            }
        ).encode()
    )

    command = _parse_notification_request(record)

    assert command.user_id == 7
    assert command.user_external_id == "user_abc"
    assert command.short == "Webhook delivered"
    assert command.payload == {"delivery_id": "d-1"}


def test_parse_missing_fields_is_poison():
    record = FakeRecord(value=json.dumps({"user_id": 7}).encode())

    with pytest.raises(PoisonError):
        _parse_notification_request(record)


def test_parse_empty_value_is_poison():
    with pytest.raises(PoisonError):
        _parse_notification_request(FakeRecord(value=None))


def test_parse_non_json_is_poison():
    with pytest.raises(PoisonError):
        _parse_notification_request(FakeRecord(value=b"not-json"))
