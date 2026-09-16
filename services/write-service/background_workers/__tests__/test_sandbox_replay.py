import json
from uuid import UUID

import pytest
from data_write_core.infrastructure.orm import OutboxEntryModel

from background_workers.management.commands.replay_sandbox_events import (
    _headers,
    _select_entries,
    _without_sandbox,
)

EVENT_ID = UUID("11111111-2222-3333-4444-555555555555")


def _entry(**overrides) -> OutboxEntryModel:
    fields = {
        "id": 42,
        "event_id": EVENT_ID,
        "aggregate_type": "transaction",
        "aggregate_id": "abc",
        "partition_key": "user_clerk_1",
        "event_type": "TransactionCreated",
        "payload": {"amount": "10.00"},
        "traceparent": "00-trace-span-01",
        "tracestate": "vendor=1",
        "baggage": "sandbox-id=nikita",
    }
    fields.update(overrides)

    return OutboxEntryModel(**fields)


def _as_dict(entry, keep_sandbox=False) -> dict:
    return {name: value.decode() for name, value in _headers(entry, keep_sandbox=keep_sandbox)}


def test_the_event_id_survives_the_replay():
    assert _as_dict(_entry())["event_id"] == str(EVENT_ID)


def test_the_outbox_sequence_is_the_original_row_id():
    assert _as_dict(_entry())["outbox_seq"] == "42"


def test_debezium_headers_are_all_reproduced():
    assert set(_as_dict(_entry(baggage="team=core"))) == {
        "event_id",
        "aggregate_type",
        "event_type",
        "outbox_seq",
        "traceparent",
        "tracestate",
        "baggage",
    }


def test_an_absent_header_is_omitted_rather_than_sent_empty():
    headers = _as_dict(_entry(traceparent=None, tracestate=None))

    assert "traceparent" not in headers
    assert "tracestate" not in headers


def test_the_sandbox_tag_is_dropped_so_the_baseline_claims_the_event():
    assert "baggage" not in _as_dict(_entry())


def test_other_baggage_members_survive_the_tag_being_dropped():
    headers = _as_dict(_entry(baggage="team=core,sandbox-id=nikita,tier=free"))

    assert headers["baggage"] == "team=core,tier=free"


def test_the_tag_can_be_kept_deliberately():
    assert _as_dict(_entry(), keep_sandbox=True)["baggage"] == "sandbox-id=nikita"


def test_stripping_a_baggage_of_only_the_tag_leaves_nothing():
    assert _without_sandbox("sandbox-id=nikita") is None


def test_stripping_tolerates_no_baggage_at_all():
    assert _without_sandbox(None) is None


def test_a_similarly_named_member_is_not_mistaken_for_the_tag():
    assert _without_sandbox("sandbox-id-2=other") == "sandbox-id-2=other"


def test_the_trace_context_is_untouched_by_stripping():
    headers = _as_dict(_entry())

    assert headers["traceparent"] == "00-trace-span-01"
    assert headers["tracestate"] == "vendor=1"


@pytest.mark.django_db(transaction=True)
async def test_only_the_named_sandboxs_events_are_selected():
    await OutboxEntryModel.objects.acreate(
        aggregate_type="transaction",
        aggregate_id="a",
        event_type="TransactionCreated",
        payload={},
        baggage="sandbox-id=nikita",
    )
    await OutboxEntryModel.objects.acreate(
        aggregate_type="transaction",
        aggregate_id="b",
        event_type="TransactionCreated",
        payload={},
        baggage="sandbox-id=someone-else",
    )
    await OutboxEntryModel.objects.acreate(
        aggregate_type="transaction",
        aggregate_id="c",
        event_type="TransactionCreated",
        payload={},
        baggage=None,
    )

    selected = _select_entries({"sandbox": "nikita", "since": None, "until": None})

    assert [entry.aggregate_id async for entry in selected] == ["a"]


def test_the_payload_is_published_as_plain_json():
    assert json.loads(json.dumps(_entry().payload)) == {"amount": "10.00"}
