from enum import StrEnum

from .config import ASCENDING_PREFIX, DESCENDING_PREFIX, GREATER_THAN_LOOKUP, LESS_THAN_LOOKUP


class SortDirection(StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"

    @property
    def opposite(self) -> "SortDirection":
        return _OPPOSITE_DIRECTIONS[self]

    @property
    def django_ordering_prefix(self) -> str:
        return _DJANGO_ORDERING_PREFIXES[self]

    @property
    def keyset_lookup(self) -> str:
        return _KEYSET_LOOKUPS[self]


_OPPOSITE_DIRECTIONS = {
    SortDirection.ASCENDING: SortDirection.DESCENDING,
    SortDirection.DESCENDING: SortDirection.ASCENDING,
}

_DJANGO_ORDERING_PREFIXES = {
    SortDirection.ASCENDING: ASCENDING_PREFIX,
    SortDirection.DESCENDING: DESCENDING_PREFIX,
}

_KEYSET_LOOKUPS = {
    SortDirection.ASCENDING: GREATER_THAN_LOOKUP,
    SortDirection.DESCENDING: LESS_THAN_LOOKUP,
}
