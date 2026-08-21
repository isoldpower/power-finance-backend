"""What a query handler hands back to a view."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FetchedRows:
    """Rows for one page — including the lookahead row — and the total behind them."""

    rows: list[Any]
    total: int
    cached: bool


@dataclass(frozen=True)
class FetchedResource:
    """A single resource and where it came from."""

    resource: Any
    cached: bool
