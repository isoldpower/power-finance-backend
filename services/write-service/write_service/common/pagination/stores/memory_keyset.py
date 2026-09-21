from collections.abc import Callable
from typing import Any

from ..ordering import SortOrder
from ..page_request import PageRequest

KeyedRow = tuple[list[Any], Any]


def keyset_slice(rows: list[Any], request: PageRequest) -> list[Any]:
    read_order = request.read_order
    keyed = [(read_order.to_cursor_values(row), row) for row in rows]
    _sort_by_order(keyed, read_order)

    anchor = request.cursor.values if request.cursor else None
    if anchor is not None:
        keyed = [pair for pair in keyed if _lies_past_anchor(pair[0], anchor, read_order)]

    return [row for _, row in keyed[: request.fetch_size]]


def _sort_by_order(keyed: list[KeyedRow], read_order: SortOrder) -> None:
    for position in reversed(range(len(read_order.keys))):
        keyed.sort(
            key=_sort_value_at(position),
            reverse=read_order.keys[position].descending,
        )


def _sort_value_at(position: int) -> Callable[[KeyedRow], Any]:
    def read_position(pair: KeyedRow) -> Any:
        return pair[0][position]

    return read_position


def _lies_past_anchor(values: list[Any], anchor: list[Any], read_order: SortOrder) -> bool:
    for key, value, anchor_value in zip(read_order.keys, values, anchor, strict=True):
        if value == anchor_value:
            continue

        return value < anchor_value if key.descending else value > anchor_value

    return False
