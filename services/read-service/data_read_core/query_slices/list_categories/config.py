from enum import IntEnum, StrEnum


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class CacheSchema(StrEnum):
    VERSION = "s1"


class ParamsList(StrEnum):
    KIND = "kind"


class Messages(StrEnum):
    UNKNOWN_KIND = "Unknown kind. Legal values: {legal}."
