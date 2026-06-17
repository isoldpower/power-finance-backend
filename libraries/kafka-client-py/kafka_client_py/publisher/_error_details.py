"""Error-detail header helpers shared by RetryPublisher and DLQPublisher.

Truncation is byte-based (not character-based) and never splits a UTF-8
sequence, matching kafka-client-go exactly: both libraries cap the same
header at the same byte budget and always emit decodable UTF-8, so a
consumer in either language can read headers produced by the other.
"""

import traceback

ERROR_MESSAGE_MAX_BYTES = 1024
ERROR_STACK_MAX_BYTES = 8192


def truncate_utf8(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def format_exception_traceback(exception: BaseException) -> str:
    return "".join(
        traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__,
        )
    )
