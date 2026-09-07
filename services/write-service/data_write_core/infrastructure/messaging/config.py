from enum import IntEnum, StrEnum


class OutboxSettings(IntEnum):
    DEFAULT_SCHEMA_VERSION = 1


class PartitionKey(StrEnum):
    GLOBAL = "GLOBAL"
