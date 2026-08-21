from abc import ABC, abstractmethod
from typing import Any

from ..cursors import CursorMinter, PageDirection
from ..ordering import SortOrder
from .scanned_rows import ScannedRows

BoundaryCursors = tuple[str | None, str | None]

NO_BOUNDARY_CURSORS: BoundaryCursors = (None, None)


class PageScan(ABC):
    """How one page is read out of a collection: which way the store walks it,
    and which of the resulting boundary rows become cursors."""

    @property
    @abstractmethod
    def direction(self) -> PageDirection:
        raise NotImplementedError()

    @abstractmethod
    def read_order(self, order: SortOrder) -> SortOrder:
        """Order the store walks in, which is not always the order the client
        reads in."""

        raise NotImplementedError()

    @abstractmethod
    def restore_reading_order(self, items: list[Any]) -> list[Any]:
        """Put the scanned rows back into the order the collection is served
        in."""

        raise NotImplementedError()

    def boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        if scanned.is_empty:
            return NO_BOUNDARY_CURSORS

        return self._boundary_cursors(scanned, minter)

    @abstractmethod
    def _boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        raise NotImplementedError()
