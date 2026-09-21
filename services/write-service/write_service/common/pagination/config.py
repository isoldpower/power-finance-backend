from enum import IntEnum, StrEnum


class LimitSettings(IntEnum):
    DEFAULT = 25
    MINIMUM = 1
    MAXIMUM = 100
    LOOKAHEAD_ROWS = 1


class ParamsList(StrEnum):
    LIMIT = "limit"
    CURSOR = "cursor"


class MetaKey(StrEnum):
    LIMIT = "limit"
    TOTAL = "total"
    NEXT_CURSOR = "next_cursor"
    PREVIOUS_CURSOR = "prev_cursor"
    CACHED = "cached"


class Messages(StrEnum):
    NON_INTEGER_LIMIT = "limit must be an integer"
