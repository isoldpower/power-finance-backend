import binascii
import json

COMPACT_SEPARATORS = (",", ":")
FINGERPRINT_LENGTH = 16
CURSOR_VERSION = 1
BASE64_BLOCK_SIZE = 4
PADDING_CHARACTER = "="

VERSION_KEY = "v"
DIRECTION_KEY = "d"
VALUES_KEY = "k"
FINGERPRINT_KEY = "f"
ORDER_KEY = "order"
QUERY_KEY = "query"

UNREADABLE_PAYLOAD_ERRORS = (
    binascii.Error,
    UnicodeDecodeError,
    json.JSONDecodeError,
    ValueError,
)
