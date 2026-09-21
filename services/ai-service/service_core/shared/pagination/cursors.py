import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from ..http_contract import ErrorCode, ValidationFailed
from .config import (
    COMPACT_SEPARATORS,
    PADDING,
    UNREADABLE,
    CursorKey,
    CursorMessage,
    CursorSettings,
)


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
    canonical = json.dumps(
        {"order": order, "query": query_material},
        sort_keys=True,
        separators=COMPACT_SEPARATORS,
        default=str,
    )

    return hashlib.sha256(canonical.encode()).hexdigest()[: CursorSettings.FINGERPRINT_LENGTH]


def encode_cursor(direction: PageDirection, values: tuple[Any, ...], fingerprint: str) -> str:
    payload = json.dumps(
        {
            CursorKey.VERSION: int(CursorSettings.VERSION),
            CursorKey.DIRECTION: str(direction),
            CursorKey.VALUES: [_encode_value(value) for value in values],
            CursorKey.FINGERPRINT: fingerprint,
        },
        separators=COMPACT_SEPARATORS,
        default=str,
    )

    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip(PADDING)


def decode_cursor(raw: str, fingerprint: str) -> Cursor:
    payload = _read_payload(raw)
    if payload.get(CursorKey.VERSION) != CursorSettings.VERSION:
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE)

    try:
        direction = PageDirection(payload[CursorKey.DIRECTION])
        values = payload[CursorKey.VALUES]
    except (KeyError, ValueError) as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE) from unreadable

    if not isinstance(values, list):
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE)
    if payload.get(CursorKey.FINGERPRINT) != fingerprint:
        raise _refuse(ErrorCode.CURSOR_MISMATCH, CursorMessage.MISMATCHED)

    return Cursor(direction=direction, values=tuple(values))


def decode_message_anchor(cursor: Cursor) -> tuple[datetime, UUID]:
    try:
        created_at, message_id = cursor.values
        return datetime.fromisoformat(str(created_at)), UUID(str(message_id))
    except (TypeError, ValueError) as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE) from unreadable


def _encode_value(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _read_payload(raw: str) -> dict:
    try:
        padded = raw + PADDING * (-len(raw) % CursorSettings.BASE64_BLOCK)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except UNREADABLE as unreadable:
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE) from unreadable

    if not isinstance(decoded, dict):
        raise _refuse(ErrorCode.CURSOR_INVALID, CursorMessage.UNREADABLE)

    return decoded


def _refuse(code: ErrorCode, message: str) -> ValidationFailed:
    return ValidationFailed(
        message=message,
        code=code,
    )
