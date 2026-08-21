from typing import Any

from ..cursors import CursorMinter, PageDirection
from ..ordering import SortOrder
from .page_scan import BoundaryCursors, PageScan
from .scanned_rows import ScannedRows


class ForwardScan(PageScan):
    """Reads on from the anchor in the collection's own order."""

    @property
    def direction(self) -> PageDirection:
        return PageDirection.NEXT

    def read_order(self, order: SortOrder) -> SortOrder:
        return order

    def restore_reading_order(self, items: list[Any]) -> list[Any]:
        return items

    def _boundary_cursors(self, scanned: ScannedRows, minter: CursorMinter) -> BoundaryCursors:
        next_cursor = minter.toward_next(scanned.last_item) if scanned.has_further_rows else None
        previous_cursor = (
            minter.toward_previous(scanned.first_item) if scanned.has_preceding_page else None
        )

        return next_cursor, previous_cursor
