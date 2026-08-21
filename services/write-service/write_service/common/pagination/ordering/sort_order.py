from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .config import SIGNATURE_SEPARATOR
from .sort_key import SortKey


@dataclass(frozen=True)
class SortOrder:
    """The lexicographic ordering a collection is served in."""

    keys: tuple[SortKey, ...]

    @property
    def signature(self) -> str:
        return SIGNATURE_SEPARATOR.join(key.signature for key in self.keys)

    @property
    def django_ordering(self) -> list[str]:
        return [key.django_ordering for key in self.keys]

    def reversed(self) -> "SortOrder":
        return SortOrder(keys=tuple(key.reversed() for key in self.keys))

    def to_cursor_values(self, row: Any) -> list[Any]:
        return [key.codec.to_cursor_value(key.read_from(row)) for key in self.keys]

    def to_anchor_values(self, cursor_values: Iterable[Any]) -> list[Any]:
        return [
            key.codec.from_cursor_value(value)
            for key, value in zip(self.keys, cursor_values, strict=True)
        ]
