from dataclasses import dataclass, replace
from typing import Any

from .config import OrderingFormat
from .row_fields import read_row_field
from .sort_direction import SortDirection
from .value_codecs import TEXT_CODEC, ValueCodec


@dataclass(frozen=True)
class SortKey:
    field: str
    direction: SortDirection = SortDirection.DESCENDING
    codec: ValueCodec = TEXT_CODEC

    @property
    def signature(self) -> str:
        return f"{self.field}:{self.direction}"

    @property
    def django_ordering(self) -> str:
        return f"{self.direction.django_ordering_prefix}{self.field}"

    @property
    def keyset_lookup_path(self) -> str:
        return f"{self.field}{OrderingFormat.DJANGO_LOOKUP_SEPARATOR}{self.direction.keyset_lookup}"

    @property
    def descending(self) -> bool:
        return self.direction is SortDirection.DESCENDING

    def reversed(self) -> "SortKey":
        return replace(self, direction=self.direction.opposite)

    def read_from(self, row: Any) -> Any:
        return read_row_field(row, self.field)
