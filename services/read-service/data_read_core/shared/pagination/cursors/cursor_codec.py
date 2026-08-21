import base64
import json
from dataclasses import dataclass
from typing import Any

from data_read_core.shared.http_contract import CursorInvalid, CursorMismatch

from .compact_json import dump_compact
from .config import (
    BASE64_BLOCK_SIZE,
    CURSOR_VERSION,
    DIRECTION_KEY,
    FINGERPRINT_KEY,
    PADDING_CHARACTER,
    UNREADABLE_PAYLOAD_ERRORS,
    VALUES_KEY,
    VERSION_KEY,
)
from .cursor import Cursor
from .page_direction import PageDirection


@dataclass(frozen=True)
class CursorCodec:
    """Turns a position into the token a client stores, and back."""

    version: int = CURSOR_VERSION

    def encode(self, direction: PageDirection, values: list[Any], fingerprint: str) -> str:
        payload = dump_compact(
            {
                VERSION_KEY: self.version,
                DIRECTION_KEY: str(direction),
                VALUES_KEY: values,
                FINGERPRINT_KEY: fingerprint,
            }
        )
        encoded = base64.urlsafe_b64encode(payload.encode()).decode()

        return encoded.rstrip(PADDING_CHARACTER)

    def decode(self, raw: str, fingerprint: str) -> Cursor:
        payload = self._read_payload(raw)
        if payload.get(VERSION_KEY) != self.version:
            raise CursorInvalid()

        cursor = self._build_cursor(payload)
        if self._require(payload, FINGERPRINT_KEY) != fingerprint:
            raise CursorMismatch()

        return cursor

    def _read_payload(self, raw: str) -> dict[str, Any]:
        try:
            padded = raw + PADDING_CHARACTER * (-len(raw) % BASE64_BLOCK_SIZE)
            decoded = json.loads(base64.urlsafe_b64decode(padded.encode()))
        except UNREADABLE_PAYLOAD_ERRORS as exc:
            raise CursorInvalid() from exc

        if not isinstance(decoded, dict):
            raise CursorInvalid()

        return decoded

    def _build_cursor(self, payload: dict[str, Any]) -> Cursor:
        try:
            direction = PageDirection(self._require(payload, DIRECTION_KEY))
        except ValueError as exc:
            raise CursorInvalid() from exc

        values = self._require(payload, VALUES_KEY)
        if not isinstance(values, list):
            raise CursorInvalid()

        return Cursor(direction=direction, values=values)

    def _require(self, payload: dict[str, Any], key: str) -> Any:
        try:
            return payload[key]
        except KeyError as exc:
            raise CursorInvalid() from exc


CURSOR_CODEC = CursorCodec()
