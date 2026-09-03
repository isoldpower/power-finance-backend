import time
from dataclasses import dataclass

from ..contracts import Overview

DEFAULT_TTL_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class _Entry:
    overview: Overview
    expires_at: float


class OverviewCache:
    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, _Entry] = {}

    def get(self, external_id: str) -> Overview | None:
        entry = self._entries.get(external_id)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(external_id, None)
            return None

        return entry.overview

    def put(self, external_id: str, overview: Overview) -> None:
        self._entries[external_id] = _Entry(
            overview=overview,
            expires_at=time.monotonic() + self._ttl,
        )

    def clear(self) -> None:
        self._entries.clear()
