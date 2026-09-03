from collections.abc import Callable
from typing import Any

from .cursors import Cursor, PageDirection, encode_cursor
from .page import Page


def build_page(
    rows: list[Any],
    total: int,
    limit: int,
    fingerprint: str,
    key_of: Callable[[Any], tuple[Any, ...]],
    cursor: Cursor | None = None,
) -> Page:
    """Trims the lookahead row and mints the cursors that navigate away from
    this page.

    `rows` is expected to hold up to `limit + 1` entries and to already be in
    the order it will be served in — a backward scan is reversed by whatever
    fetched it, so this only ever sees newest-first.
    """

    backwards = cursor is not None and cursor.backwards
    has_more = len(rows) > limit
    if has_more:
        rows = rows[-limit:] if backwards else rows[:limit]

    if not rows:
        return Page(items=rows, total=total, limit=limit)

    return Page(
        items=rows,
        total=total,
        limit=limit,
        next_cursor=(
            encode_cursor(PageDirection.NEXT, key_of(rows[-1]), fingerprint)
            if backwards or has_more
            else None
        ),
        previous_cursor=(
            encode_cursor(PageDirection.PREVIOUS, key_of(rows[0]), fingerprint)
            if cursor is not None and (not backwards or has_more)
            else None
        ),
    )
