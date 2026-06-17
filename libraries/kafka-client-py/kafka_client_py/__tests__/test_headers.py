"""Kafka header utilities: encode/decode/get/merge for stringly-typed header values.

These functions are the entire wire format for our retry/DLQ
metadata. Pin both the happy paths and the lenient edges (None inputs,
unparseable values, missing headers) — callers expect this surface to
be forgiving so they never crash on a malformed inbound message.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from kafka_client_py import headers as H


def test_encode_decode_roundtrip_string():
    assert H.decode(H.encode("hello")) == "hello"


def test_encode_decode_roundtrip_int():
    assert H.decode(H.encode(42)) == "42"
    assert H.get_int([(H.HEADER_RETRY_COUNT, H.encode(42))], H.HEADER_RETRY_COUNT) == 42


def test_encode_datetime_naive_is_treated_as_utc():
    naive = datetime(2026, 5, 18, 12, 0, 0)
    raw = H.encode(naive)
    parsed = datetime.fromisoformat(raw.decode())

    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def test_encode_datetime_non_utc_is_normalised_to_utc():
    plus_three = timezone(timedelta(hours=3))
    aware = datetime(2026, 5, 18, 15, 0, 0, tzinfo=plus_three)
    raw = H.encode(aware)
    parsed = datetime.fromisoformat(raw.decode())

    assert parsed == datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def test_decode_returns_none_for_none_input():
    assert H.decode(None) is None


def test_encode_bool_becomes_string_repr():
    assert H.decode(H.encode(True)) == "True"  # type: ignore[arg-type]


def test_get_returns_none_when_headers_iterable_is_none():
    assert H.get(None, "x") is None


def test_get_returns_none_when_headers_iterable_is_empty():
    assert H.get([], "x") is None


def test_get_returns_none_when_header_name_absent():
    assert H.get([("a", b"1")], "b") is None


def test_get_returns_last_occurrence_when_header_repeats():
    hs = [("x", b"first"), ("x", b"second")]

    assert H.get(hs, "x") == "second"


def test_get_int_default_on_missing_headers():
    assert H.get_int(None, "nope", default=7) == 7


def test_get_int_default_on_unparseable_value():
    assert H.get_int([("nope", b"not-a-number")], "nope", default=9) == 9


def test_get_int_parses_valid_integer_string():
    assert H.get_int([("n", H.encode(123))], "n") == 123


def test_get_int_handles_negative_integer():
    assert H.get_int([("n", H.encode(-5))], "n") == -5


def test_get_int_default_zero_when_no_default_provided():
    assert H.get_int(None, "nope") == 0


def test_get_datetime_roundtrips_via_encode():
    original = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
    hs = [(H.HEADER_RETRY_AT, H.encode(original))]

    assert H.get_datetime(hs, H.HEADER_RETRY_AT) == original


def test_get_datetime_returns_none_when_header_absent():
    assert H.get_datetime([], "nope") is None


def test_get_datetime_returns_none_on_malformed_value():
    assert H.get_datetime([("ts", b"not a date")], "ts") is None


def test_get_datetime_returns_none_when_headers_is_none():
    assert H.get_datetime(None, "ts") is None


def test_merge_does_not_mutate_input():
    base = [("a", b"1")]

    merged = H.merge(base, ("b", "2"))

    assert base == [("a", b"1")]
    assert ("b", b"2") in merged


def test_merge_with_none_base_returns_only_additions():
    merged = H.merge(None, ("a", "1"), ("b", "2"))

    assert merged == [("a", b"1"), ("b", b"2")]


def test_merge_preserves_addition_order():
    merged = H.merge([], ("a", "1"), ("b", "2"), ("c", "3"))

    assert [name for name, _ in merged] == ["a", "b", "c"]


def test_merge_appends_duplicates_rather_than_replacing():
    base = [("retry-count", b"1")]

    merged = H.merge(base, ("retry-count", 2))

    assert merged == [("retry-count", b"1"), ("retry-count", b"2")]


def test_merge_with_no_additions_copies_base():
    base = [("a", b"1")]

    merged = H.merge(base)

    assert merged == base
    assert merged is not base
