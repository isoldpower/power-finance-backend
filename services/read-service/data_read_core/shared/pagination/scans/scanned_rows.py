from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScannedRows:
    """One scan's result: the page in reading order, plus what its neighbours
    are."""

    items: list[Any]
    has_further_rows: bool
    has_preceding_page: bool

    @property
    def is_empty(self) -> bool:
        return not self.items

    @property
    def first_item(self) -> Any:
        return self.items[0]

    @property
    def last_item(self) -> Any:
        return self.items[-1]
