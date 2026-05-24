import json
from typing import Any

STATE_IN_FLIGHT = "in_flight"
STATE_COMPLETED = "completed"


class EntryCodec:
    @staticmethod
    def encode_lock_entry(request_hash: str) -> str:
        return json.dumps(
            {"state": STATE_IN_FLIGHT, "request_hash": request_hash},
            separators=(",", ":"),
        )

    @staticmethod
    def encode_completed_entry(
        *,
        request_hash: str,
        status_code: int,
        body: Any,
        headers: dict[str, str],
    ) -> str:
        return json.dumps(
            {
                "state": STATE_COMPLETED,
                "request_hash": request_hash,
                "status_code": status_code,
                "body": body,
                "headers": headers,
            },
            separators=(",", ":"),
            default=str,
        )

    @staticmethod
    def decode_entry(raw_entry: str | bytes | None) -> dict[str, Any] | None:
        if raw_entry is None:
            return None
        if isinstance(raw_entry, bytes):
            raw_entry = raw_entry.decode("utf-8")
        try:
            return json.loads(raw_entry)
        except (json.JSONDecodeError, TypeError):
            return None


__all__ = [
    "STATE_COMPLETED",
    "STATE_IN_FLIGHT",
    "EntryCodec",
]
