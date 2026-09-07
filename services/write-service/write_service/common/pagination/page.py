from dataclasses import dataclass
from typing import Any

from .config import MetaKey


@dataclass(frozen=True)
class Page:
    items: list[Any]
    total: int
    limit: int | None = None
    next_cursor: str | None = None
    previous_cursor: str | None = None

    def meta(self, *, cached: bool | None = None, namespace: str | None = None) -> dict[str, Any]:
        block: dict[str, Any] = {
            MetaKey.LIMIT: self.limit,
            MetaKey.TOTAL: self.total,
            MetaKey.NEXT_CURSOR: self.next_cursor,
            MetaKey.PREVIOUS_CURSOR: self.previous_cursor,
        }
        meta: dict[str, Any] = {namespace: block} if namespace else dict(block)

        if cached is not None:
            meta[MetaKey.CACHED] = cached

        return meta


class CompletePage(Page):
    def __init__(self, items: list[Any], *, total: int | None = None) -> None:
        super().__init__(items=items, total=total if total is not None else len(items))
