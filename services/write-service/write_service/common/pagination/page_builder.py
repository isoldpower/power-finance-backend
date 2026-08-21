from typing import Any

from .page import Page
from .page_request import PageRequest
from .scans import ScannedRows


def build_page(rows: list[Any], total: int, request: PageRequest) -> Page:
    """Trim the lookahead row, restore reading order, and mint both cursors."""

    scan = request.scan
    scanned = ScannedRows(
        items=scan.restore_reading_order(list(rows[: request.limit])),
        has_further_rows=len(rows) > request.limit,
        has_preceding_page=not request.is_first_request,
    )
    next_cursor, previous_cursor = scan.boundary_cursors(
        scanned,
        request.cursor_minter,
    )

    return Page(
        items=scanned.items,
        total=total,
        limit=request.limit,
        next_cursor=next_cursor,
        previous_cursor=previous_cursor,
    )
