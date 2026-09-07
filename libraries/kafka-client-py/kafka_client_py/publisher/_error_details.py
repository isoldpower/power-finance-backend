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
