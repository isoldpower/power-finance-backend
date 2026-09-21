import json
from dataclasses import dataclass, field
from uuid import UUID

import pytest
from data_write_core.domain.automations import TriggerEvent
from kafka_client_py import PoisonError, envelope as KafkaEnvelope

from background_workers.services.automation_engine import (
    EVENT_AUTOMATION_HANDLERS,
    TRIGGER_BY_EVENT_TYPE,
    handle_automation_event,
)
from background_workers.services.automation_engine.config import AutomationEngineConfig

TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@dataclass
class FakeRecord:
    value: bytes | None
    topic: str = "events.async"
    partition: int = 0
    offset: int = 0
    key: bytes | None = None
    headers: tuple = field(default_factory=tuple)


def record(event_type: str, body: dict, key: bytes = b"user_abc") -> FakeRecord:
    return FakeRecord(
        value=json.dumps(body).encode(),
        key=key,
        headers=(
            (KafkaEnvelope.HEADER_EVENT_ID, b"e-1"),
            (KafkaEnvelope.HEADER_EVENT_TYPE, event_type.encode()),
        ),
    )


def test_both_kinds_of_edit_are_the_same_trigger():
    assert TRIGGER_BY_EVENT_TYPE["TransactionUpdated"] is TriggerEvent.TRANSACTION_UPDATED
    assert TRIGGER_BY_EVENT_TYPE["TransactionMetadataUpdated"] is TriggerEvent.TRANSACTION_UPDATED
    assert TRIGGER_BY_EVENT_TYPE["TransactionCreated"] is TriggerEvent.TRANSACTION_CREATED


def test_deletion_is_not_a_trigger():
    assert "TransactionDeleted" not in TRIGGER_BY_EVENT_TYPE


async def test_an_event_no_rule_can_trigger_on_is_ignored_rather_than_poisoned():
    await handle_automation_event(record("WalletCreated", {"wallet_id": "w-1"}))


async def test_a_message_without_envelope_headers_is_poison():
    await_error = FakeRecord(value=b"{}")

    with pytest.raises(PoisonError):
        await handle_automation_event(await_error)


async def test_a_transaction_event_without_a_subject_is_poison():
    with pytest.raises(PoisonError):
        await handle_automation_event(record("TransactionCreated", {"user_id": 7}))


def test_the_subject_comes_off_the_payload():
    handler = EVENT_AUTOMATION_HANDLERS["TransactionCreated"]
    payload = handler.decode(json.dumps({"transaction_id": TX_ID, "user_id": "7"}).encode())

    assert (handler.subject_id(payload), handler.user_id(payload)) == (UUID(TX_ID), 7)


def test_one_handler_serves_every_transaction_event():
    served = {
        event_type
        for event_type, handler in EVENT_AUTOMATION_HANDLERS.items()
        if handler.subject == "transaction"
    }

    assert served == {"TransactionCreated", "TransactionUpdated", "TransactionMetadataUpdated"}


def test_the_registry_agrees_with_what_each_handler_says_it_serves():
    assert all(
        handler.serves(event_type) for event_type, handler in EVENT_AUTOMATION_HANDLERS.items()
    )


def test_the_engine_starts_at_the_end_of_the_topic():
    config = AutomationEngineConfig(
        bootstrap_servers="kafka:9092",
        group_id="write-service.automation-engine",
        topics=["events.async"],
    )

    assert config.auto_offset_reset == "latest"
    assert config.kafka.auto_offset_reset == "latest"
