"""Header conventions for events.retry and events.dlq.

Kafka headers are `list[tuple[str, bytes]]` on the wire. This module centralises
the names and gives typed encode/decode helpers so every producer/consumer in
the system agrees on the contract.

`x-` prefix is a deliberate choice: these are transport-layer routing /
diagnostic headers, distinct from any business headers a payload may carry.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

KafkaHeaders = list[tuple[str, bytes]]


# Routing
HEADER_ORIGINAL_TOPIC = "x-original-topic"
HEADER_ORIGINAL_PARTITION = "x-original-partition"
HEADER_ORIGINAL_OFFSET = "x-original-offset"

# Retry budget
HEADER_RETRY_COUNT = "x-retry-count"  # total attempts including in-process
HEADER_RETRY_AT = "x-retry-at"  # ISO-8601 UTC; retry consumer sleeps until this
HEADER_FIRST_FAILED_AT = "x-first-failed-at"

# Error diagnostics
HEADER_ERROR_CLASS = "x-error-class"
HEADER_ERROR_MESSAGE = "x-error-message"
HEADER_ERROR_STACK = "x-error-stack"
HEADER_FAILED_AT = "x-failed-at"

# Correlation (mirrors the value already carried on the wire end-to-end)
HEADER_CORRELATION_ID = "x-correlation-id"


def encode(value: str | int | datetime) -> bytes:
    """Encode a header value to UTF-8 bytes."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().encode("utf-8")
    return str(value).encode("utf-8")


def decode(value: bytes | None) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8")


def get(headers: Iterable[tuple[str, bytes]] | None, name: str) -> str | None:
    """Case-sensitive header lookup. Returns the *last* occurrence."""
    if not headers:
        return None
    found: bytes | None = None
    for k, v in headers:
        if k == name:
            found = v
    return decode(found)


def get_int(headers: Iterable[tuple[str, bytes]] | None, name: str, default: int = 0) -> int:
    raw = get(headers, name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_datetime(headers: Iterable[tuple[str, bytes]] | None, name: str) -> datetime | None:
    raw = get(headers, name)
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def merge(base: KafkaHeaders | None, *additions: tuple[str, str | int | datetime]) -> KafkaHeaders:
    """Return a new header list with the additions appended (encoded)."""
    out: KafkaHeaders = list(base) if base else []
    for name, value in additions:
        out.append((name, encode(value)))
    return out
