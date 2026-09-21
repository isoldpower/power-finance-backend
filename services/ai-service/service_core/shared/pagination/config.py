import binascii
import json
from enum import IntEnum, StrEnum


class LimitSettings(IntEnum):
    DEFAULT = 25
    MINIMUM = 1
    MAXIMUM = 100


class ParamsList(StrEnum):
    LIMIT = "limit"


class LimitMessage(StrEnum):
    NON_INTEGER = "limit must be an integer."


class OrderSettings(StrEnum):
    MESSAGE_FEED = "created_at:desc,id:desc"


class CursorSettings(IntEnum):
    VERSION = 1
    FINGERPRINT_LENGTH = 16
    BASE64_BLOCK = 4


class CursorKey(StrEnum):
    VERSION = "v"
    DIRECTION = "d"
    VALUES = "k"
    FINGERPRINT = "f"


class CursorMessage(StrEnum):
    UNREADABLE = "This cursor cannot be read."
    MISMATCHED = "This cursor belongs to a different query."


PADDING = "="
COMPACT_SEPARATORS = (",", ":")

UNREADABLE: tuple[type[BaseException], ...] = (
    binascii.Error,
    UnicodeDecodeError,
    json.JSONDecodeError,
    ValueError,
)
