import base64
import json
from dataclasses import dataclass
from typing import Any

from write_service.common.http_contract import CursorInvalid, CursorMismatch

from .compact_json import dump_compact
from .config import (
    PADDING_CHARACTER,
    UNREADABLE_PAYLOAD_ERRORS,
    CursorKey,
    CursorSettings,
)
from .cursor import Cursor
from .page_direction import PageDirection


@dataclass(frozen=True)
class CursorCodec:
    version: int = int(CursorSettings.VERSION)

    def encode(self, direction: PageDirection, values: list[Any], fingerprint: str) -> str:
        payload = dump_compact(
            {
                CursorKey.VERSION: self.version,
                CursorKey.DIRECTION: str(direction),
                CursorKey.VALUES: values,
                CursorKey.FINGERPRINT: fingerprint,
            }
        )
        encoded = base64.urlsafe_b64encode(payload.encode()).decode()

        return encoded.rstrip(PADDING_CHARACTER)

    def decode(self, raw: str, fingerprint: str) -> Cursor:
        payload = self._read_payload(raw)
        if payload.get(CursorKey.VERSION) != self.version:
            raise CursorInvalid()

        cursor = self._build_cursor(payload)
        if self._require(payload, CursorKey.FINGERPRINT) != fingerprint:
            raise CursorMismatch()

        return cursor

    def _read_payload(self, raw: str) -> dict[str, Any]:
        try:
            padded = raw + PADDING_CHARACTER * (-len(raw) % CursorSettings.BASE64_BLOCK_SIZE)
            decoded = json.loads(base64.urlsafe_b64decode(padded.encode()))
        except UNREADABLE_PAYLOAD_ERRORS as exc:
            raise CursorInvalid() from exc

        if not isinstance(decoded, dict):
            raise CursorInvalid()

        return decoded

    def _build_cursor(self, payload: dict[str, Any]) -> Cursor:
        try:
            direction = PageDirection(self._require(payload, CursorKey.DIRECTION))
        except ValueError as exc:
            raise CursorInvalid() from exc

        values = self._require(payload, CursorKey.VALUES)
        if not isinstance(values, list):
            raise CursorInvalid()

        return Cursor(direction=direction, values=values)

    def _require(self, payload: dict[str, Any], key: str) -> Any:
        try:
            return payload[key]
        except KeyError as exc:
            raise CursorInvalid() from exc


CURSOR_CODEC = CursorCodec()
