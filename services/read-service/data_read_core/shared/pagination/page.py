from dataclasses import dataclass
from typing import Any

from .config import KEYS


@dataclass(frozen=True)
class Page:
    """A materialized page plus the two cursors that navigate away from it."""

    items: list[Any]
    total: int
    limit: int | None = None
    next_cursor: str | None = None
    previous_cursor: str | None = None

    def meta(self, *, cached: bool | None = None, namespace: str | None = None) -> dict[str, Any]:
        block = {
            KEYS.get("LIMIT"): self.limit,
            KEYS.get("TOTAL"): self.total,
            KEYS.get("NEXT_CURSOR"): self.next_cursor,
            KEYS.get("PREVIOUS_CURSOR"): self.previous_cursor,
        }
        meta: dict[str, Any] = {namespace: block} if namespace else dict(block)

        if cached is not None:
            meta[KEYS.get("CACHED")] = cached

        return meta


class CompletePage(Page):
    """For the handful of endpoints that return a fixed, complete set."""

    def __init__(self, items: list[Any], *, total: int | None = None) -> None:
        super().__init__(items=items, total=total if total is not None else len(items))
