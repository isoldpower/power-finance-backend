from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FetchedRows:
    rows: list[Any]
    total: int
    cached: bool


@dataclass(frozen=True)
class FetchedResource:
    resource: Any
    cached: bool
