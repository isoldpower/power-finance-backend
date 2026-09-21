from enum import IntEnum, StrEnum


class HeaderName(StrEnum):
    IDEMPOTENCY_KEY = "Idempotency-Key"
    REPLAYED = "Idempotent-Replayed"


class MetaKey(StrEnum):
    REPLAY = "idempotent_replay"


class EntryState(StrEnum):
    IN_FLIGHT = "in_flight"
    COMPLETED = "completed"


class IdempotencySettings(IntEnum):
    MAX_KEY_LENGTH = 255


ANONYMOUS_USER_ID = "anonymous"
