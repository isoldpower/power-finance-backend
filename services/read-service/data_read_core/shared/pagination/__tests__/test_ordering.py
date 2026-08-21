from datetime import UTC, datetime

import pytest

from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    DATETIME_CODEC,
    INTEGER_CODEC,
    UUID_CODEC,
    SortDirection,
)

MOMENT = datetime(2026, 1, 1, tzinfo=UTC)
MOMENT_IN_MILLISECONDS = int(MOMENT.timestamp() * 1000)


@pytest.mark.parametrize("value", [MOMENT, MOMENT.isoformat()])
def test_timestamps_encode_the_same_from_a_model_or_a_document(value):
    """Postgres rows arrive holding `datetime`s and Elasticsearch hits arrive
    already serialised; one collection can be paged through either."""

    assert DATETIME_CODEC.to_cursor_value(value) == MOMENT.isoformat()


def test_timestamps_decode_back_to_an_aware_datetime():
    assert DATETIME_CODEC.from_cursor_value(MOMENT.isoformat()) == MOMENT


def test_timestamps_reach_elasticsearch_as_epoch_milliseconds():
    assert DATETIME_CODEC.to_elasticsearch_value(MOMENT.isoformat()) == MOMENT_IN_MILLISECONDS


@pytest.mark.parametrize("codec", [DATETIME_CODEC, INTEGER_CODEC, UUID_CODEC])
def test_absent_values_stay_absent_in_every_representation(codec):
    assert codec.to_cursor_value(None) is None
    assert codec.from_cursor_value(None) is None
    assert codec.to_elasticsearch_value(None) is None


def test_reversing_an_order_flips_every_key():
    reversed_order = CREATED_AT_DESC.reversed()

    assert [key.direction for key in reversed_order.keys] == [SortDirection.ASCENDING] * 2
    assert reversed_order.django_ordering == ["created_at", "id"]
    assert reversed_order.reversed() == CREATED_AT_DESC


def test_keyset_lookup_follows_the_direction_of_each_key():
    ascending = CREATED_AT_DESC.reversed().keys[0]
    descending = CREATED_AT_DESC.keys[0]

    assert descending.keyset_lookup_path == "created_at__lt"
    assert ascending.keyset_lookup_path == "created_at__gt"


def test_signature_names_the_order_a_cursor_was_minted_for():
    assert CREATED_AT_DESC.signature == "created_at:desc,id:desc"
    assert CREATED_AT_DESC.reversed().signature == "created_at:asc,id:asc"
