from abc import ABC, abstractmethod
from typing import Any

from ..cursors import CursorMinter, PageDirection
from ..ordering import SortOrder
from .scanned_rows import ScannedRows

BoundaryCursors = tuple[str | None, str | None]

NO_BOUNDARY_CURSORS: BoundaryCursors = (None, None)


class PageScan(ABC):
    @property
    @abstractmethod
    def direction(self) -> PageDirection:
        raise NotImplementedError()

    @abstractmethod
    def read_order(self, order: SortOrder) -> SortOrder:
        raise NotImplementedError()

    @abstractmethod
    def restore_reading_order(self, items: list[Any]) -> list[Any]:
        raise NotImplementedError()

    def boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        if scanned.is_empty:
            return NO_BOUNDARY_CURSORS

        return self._boundary_cursors(scanned, minter)

    @abstractmethod
    def _boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        raise NotImplementedError()
