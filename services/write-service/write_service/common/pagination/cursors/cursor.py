from dataclasses import dataclass
from typing import Any

from .page_direction import PageDirection


@dataclass(frozen=True)
class Cursor:
    direction: PageDirection
    values: list[Any]
