from dataclasses import dataclass, replace
from typing import Any

from .config import DJANGO_LOOKUP_SEPARATOR
from .row_fields import read_row_field
from .sort_direction import SortDirection
from .value_codecs import TEXT_CODEC, ValueCodec


@dataclass(frozen=True)
class SortKey:
    """One component of an ordering: the field, the direction it runs in, and
    how its values survive a round trip through a cursor."""

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
        return f"{self.field}{DJANGO_LOOKUP_SEPARATOR}{self.direction.keyset_lookup}"

    @property
    def descending(self) -> bool:
        """Asked by the in-memory store, which sorts rather than emits a lookup."""

        return self.direction is SortDirection.DESCENDING

    def reversed(self) -> "SortKey":
        return replace(self, direction=self.direction.opposite)

    def read_from(self, row: Any) -> Any:
        return read_row_field(row, self.field)
