import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from service_core.shared.http_contract import ErrorCode, ValidationFailed

# The wire format the Django services mint, restated here so a client stores
# one kind of opaque token whichever service answered it.
CURSOR_VERSION = 1
FINGERPRINT_LENGTH = 16
COMPACT_SEPARATORS = (",", ":")
PADDING = "="
BASE64_BLOCK = 4

VERSION_KEY = "v"
DIRECTION_KEY = "d"
VALUES_KEY = "k"
FINGERPRINT_KEY = "f"

UNREADABLE = (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError)


class PageDirection(StrEnum):
    NEXT = "next"
    PREVIOUS = "prev"


@dataclass(frozen=True, slots=True)
class Cursor:
    direction: PageDirection
    values: tuple[Any, ...]

    @property
    def backwards(self) -> bool:
        return self.direction is PageDirection.PREVIOUS


def query_fingerprint(order: str, query_material: Any = None) -> str:
    """Binds a cursor to the query that produced it, so one carried across a
    filter change is refused instead of silently skipping rows."""

    canonical = json.dumps(
        {"order": order, "query": query_material},
        sort_keys=True,
        separators=COMPACT_SEPARATORS,
        default=str,
    )

    return hashlib.sha256(canonical.encode()).hexdigest()[:FINGERPRINT_LENGTH]


def encode_cursor(direction: PageDirection, values: tuple[Any, ...], fingerprint: str) -> str:
    payload = json.dumps(
        {
            VERSION_KEY: CURSOR_VERSION,
            DIRECTION_KEY: str(direction),
            VALUES_KEY: [_encode_value(value) for value in values],
            FINGERPRINT_KEY: fingerprint,
        },
        separators=COMPACT_SEPARATORS,
        default=str,
    )

    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip(PADDING)


def decode_cursor(raw: str, fingerprint: str) -> Cursor:
    payload = _read_payload(raw)
    if payload.get(VERSION_KEY) != CURSOR_VERSION:
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.")

    try:
        direction = PageDirection(payload[DIRECTION_KEY])
        values = payload[VALUES_KEY]
    except (KeyError, ValueError) as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.") from unreadable

    if not isinstance(values, list):
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.")
    if payload.get(FINGERPRINT_KEY) != fingerprint:
        raise _refuse(ErrorCode.CURSOR_MISMATCH, "This cursor belongs to a different query.")

    return Cursor(direction=direction, values=tuple(values))


def decode_message_anchor(cursor: Cursor) -> tuple[datetime, UUID]:
    """The one keyset this service pages on: `created_at DESC, id DESC`."""

    try:
        created_at, message_id = cursor.values
        return datetime.fromisoformat(str(created_at)), UUID(str(message_id))
    except (TypeError, ValueError) as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.") from unreadable


def _encode_value(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _read_payload(raw: str) -> dict:
    try:
        padded = raw + PADDING * (-len(raw) % BASE64_BLOCK)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except UNREADABLE as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.") from unreadable

    if not isinstance(decoded, dict):
        raise _refuse(ErrorCode.CURSOR_INVALID, "This cursor cannot be read.")

    return decoded


def _refuse(code: ErrorCode, message: str) -> ValidationFailed:
    return ValidationFailed(message=message, code=code)
