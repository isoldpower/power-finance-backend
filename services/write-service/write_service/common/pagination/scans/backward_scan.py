from typing import Any

from ..cursors import CursorMinter, PageDirection
from ..ordering import SortOrder
from .page_scan import BoundaryCursors, PageScan
from .scanned_rows import ScannedRows


class BackwardScan(PageScan):
    """Reads back toward the head of the collection."""

    @property
    def direction(self) -> PageDirection:
        return PageDirection.PREVIOUS

    def read_order(self, order: SortOrder) -> SortOrder:
        return order.reversed()

    def restore_reading_order(self, items: list[Any]) -> list[Any]:
        return list(reversed(items))

    def _boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        # We arrived from a later page, so a next page always exists.
        next_cursor = minter.toward_next(scanned.last_item)
        previous_cursor = (
            minter.toward_previous(scanned.first_item) if scanned.has_further_rows else None
        )

        return next_cursor, previous_cursor
