import binascii
import json
from enum import IntEnum, StrEnum


class CursorSettings(IntEnum):
    VERSION = 1
    FINGERPRINT_LENGTH = 16
    BASE64_BLOCK_SIZE = 4


class CursorKey(StrEnum):
    VERSION = "v"
    DIRECTION = "d"
    VALUES = "k"
    FINGERPRINT = "f"


class FingerprintKey(StrEnum):
    ORDER = "order"
    QUERY = "query"


COMPACT_SEPARATORS = (",", ":")
PADDING_CHARACTER = "="

UNREADABLE_PAYLOAD_ERRORS = (
    binascii.Error,
    UnicodeDecodeError,
    json.JSONDecodeError,
    ValueError,
)
