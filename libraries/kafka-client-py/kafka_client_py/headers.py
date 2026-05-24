from collections.abc import Iterable
from datetime import UTC, datetime

KafkaHeaders = list[tuple[str, bytes]]


HEADER_ORIGINAL_TOPIC = "x-original-topic"
HEADER_ORIGINAL_PARTITION = "x-original-partition"
HEADER_ORIGINAL_OFFSET = "x-original-offset"

HEADER_RETRY_COUNT = "x-retry-count"
HEADER_RETRY_AT = "x-retry-at"
HEADER_FIRST_FAILED_AT = "x-first-failed-at"

HEADER_ERROR_CLASS = "x-error-class"
HEADER_ERROR_MESSAGE = "x-error-message"
HEADER_ERROR_STACK = "x-error-stack"
HEADER_FAILED_AT = "x-failed-at"

HEADER_CORRELATION_ID = "x-correlation-id"


def encode(value: str | int | datetime) -> bytes:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().encode("utf-8")

    return str(value).encode("utf-8")


def decode(value: bytes | None) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8")


def get(
    headers: Iterable[tuple[str, bytes]] | None,
    name: str,
) -> str | None:
    if not headers:
        return None
    last_match_bytes: bytes | None = None
    for header_name, header_value in headers:
        if header_name == name:
            last_match_bytes = header_value
    return decode(last_match_bytes)


def get_int(
    headers: Iterable[tuple[str, bytes]] | None,
    name: str,
    default: int = 0,
) -> int:
    raw_header_value = get(headers, name)
    if raw_header_value is None:
        return default

    try:
        return int(raw_header_value)
    except ValueError:
        return default


def get_datetime(
    headers: Iterable[tuple[str, bytes]] | None,
    name: str,
) -> datetime | None:
    raw_header_value = get(headers, name)
    if raw_header_value is None:
        return None

    try:
        return datetime.fromisoformat(raw_header_value)
    except ValueError:
        return None


def merge(
    base: KafkaHeaders | None,
    *additions: tuple[str, str | int | datetime],
) -> KafkaHeaders:
    merged_headers: KafkaHeaders = list(base) if base else []
    for name, value in additions:
        merged_headers.append((name, encode(value)))

    return merged_headers
