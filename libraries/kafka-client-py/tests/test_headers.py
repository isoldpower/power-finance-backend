from __future__ import annotations

from datetime import UTC, datetime

from kafka_client_py import headers as H


def test_encode_decode_roundtrip_string():
    assert H.decode(H.encode("hello")) == "hello"


def test_encode_decode_roundtrip_int():
    assert H.decode(H.encode(42)) == "42"
    assert H.get_int([(H.HEADER_RETRY_COUNT, H.encode(42))], H.HEADER_RETRY_COUNT) == 42


def test_encode_datetime_serialises_as_utc_iso():
    naive = datetime(2026, 5, 18, 12, 0, 0)
    raw = H.encode(naive)
    parsed = datetime.fromisoformat(raw.decode())
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def test_get_returns_last_occurrence():
    hs = [("x", b"first"), ("x", b"second")]
    assert H.get(hs, "x") == "second"


def test_merge_does_not_mutate_input():
    base = [("a", b"1")]
    merged = H.merge(base, ("b", "2"))
    assert base == [("a", b"1")]
    assert ("b", b"2") in merged


def test_get_int_default_on_missing_or_bad():
    assert H.get_int(None, "nope", default=7) == 7
    assert H.get_int([("nope", b"not-a-number")], "nope", default=9) == 9
