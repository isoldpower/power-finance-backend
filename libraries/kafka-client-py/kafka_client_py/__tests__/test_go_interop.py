"""Wire-compatibility pins against kafka-client-go.

A producer may run the Python library while the consumer runs the Go one
(or vice versa), so every encoding this library reads or writes must be
parseable by the Go library and vice versa. These tests pin the exact
formats the Go side emits; if one fails, the contract is broken and the
Go library (libraries/kafka-client-go) must be checked together with it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kafka_client_py import headers as H
from kafka_client_py.publisher._error_details import (
    ERROR_MESSAGE_MAX_BYTES,
    truncate_utf8,
)

GO_ENCODED_TIMESTAMPS = [
    ("2026-01-02T03:04:05Z", datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)),
    ("2026-01-02T03:04:05.1Z", datetime(2026, 1, 2, 3, 4, 5, 100000, tzinfo=UTC)),
    ("2026-01-02T03:04:05.123456Z", datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)),
    ("2026-01-02T03:04:05.123456789Z", datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)),
]


@pytest.mark.parametrize(("go_encoded", "expected"), GO_ENCODED_TIMESTAMPS)
def test_get_datetime_parses_go_rfc3339_formats(go_encoded: str, expected: datetime):
    headers = [(H.HEADER_RETRY_AT, go_encoded.encode("utf-8"))]

    assert H.get_datetime(headers, H.HEADER_RETRY_AT) == expected


def test_python_isoformat_stays_parseable_as_rfc3339():
    encoded = H.encode(datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)).decode("utf-8")

    assert encoded == "2026-01-02T03:04:05.123456+00:00"


def test_truncate_utf8_caps_by_bytes_like_go():
    three_byte_character = "€"
    truncated = truncate_utf8(three_byte_character * 600, ERROR_MESSAGE_MAX_BYTES)

    encoded = truncated.encode("utf-8")
    assert len(encoded) <= ERROR_MESSAGE_MAX_BYTES
    assert len(encoded) == ERROR_MESSAGE_MAX_BYTES - ERROR_MESSAGE_MAX_BYTES % 3


def test_truncate_utf8_never_produces_undecodable_bytes():
    truncated = truncate_utf8("é" * 600, ERROR_MESSAGE_MAX_BYTES)

    truncated.encode("utf-8").decode("utf-8")


def test_truncate_utf8_is_noop_within_budget():
    assert truncate_utf8("short", ERROR_MESSAGE_MAX_BYTES) == "short"


def _go_truncate(raw: bytes, max_bytes: int) -> bytes:
    while max_bytes > 0 and (raw[max_bytes] & 0xC0) == 0x80:
        max_bytes -= 1
    return raw[:max_bytes]


def test_go_truncated_header_bytes_decode_cleanly():
    two_byte_character = "é"
    raw = (two_byte_character * 600).encode("utf-8")

    go_truncated = _go_truncate(raw, ERROR_MESSAGE_MAX_BYTES - 1)

    assert H.decode(go_truncated) == two_byte_character * ((ERROR_MESSAGE_MAX_BYTES - 2) // 2)
