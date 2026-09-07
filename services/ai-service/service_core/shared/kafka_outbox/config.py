from enum import IntEnum, StrEnum


class OutboxSettings(IntEnum):
    SCHEMA_VERSION = 1


class OutboxColumn(StrEnum):
    EVENT_ID = "event_id"
    AGGREGATE_TYPE = "aggregate_type"
    AGGREGATE_ID = "aggregate_id"
    PARTITION_KEY = "partition_key"
    EVENT_TYPE = "event_type"
    PAYLOAD = "payload"
    OCCURRED_AT = "occurred_at"
