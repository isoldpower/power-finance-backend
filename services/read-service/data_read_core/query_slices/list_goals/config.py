from enum import IntEnum, StrEnum


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class CacheSchema(StrEnum):
    VERSION = "s1"
