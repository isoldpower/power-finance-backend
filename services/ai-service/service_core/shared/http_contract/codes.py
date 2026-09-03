from enum import StrEnum
from http import HTTPStatus


class ErrorCode(StrEnum):
    """The top-level `error.code`, each member carrying the status it is served
    with — the same table the Django services keep, narrowed to what this
    service can actually emit."""

    _status_code: int

    def __new__(cls, wire_code: str, status_code: int) -> "ErrorCode":
        member = str.__new__(cls, wire_code)
        member._value_ = wire_code
        member._status_code = status_code

        return member

    BAD_REQUEST = ("bad_request", HTTPStatus.BAD_REQUEST)
    UNAUTHORIZED = ("unauthorized", HTTPStatus.UNAUTHORIZED)
    NOT_FOUND = ("not_found", HTTPStatus.NOT_FOUND)
    VALIDATION_FAILED = ("validation_failed", HTTPStatus.UNPROCESSABLE_ENTITY)
    CURSOR_INVALID = ("cursor_invalid", HTTPStatus.UNPROCESSABLE_ENTITY)
    CURSOR_MISMATCH = ("cursor_mismatch", HTTPStatus.UNPROCESSABLE_ENTITY)
    INTERNAL_ERROR = ("internal_error", HTTPStatus.INTERNAL_SERVER_ERROR)
    ASSISTANT_UNAVAILABLE = ("assistant_unavailable", HTTPStatus.SERVICE_UNAVAILABLE)

    @property
    def status_code(self) -> int:
        return int(self._status_code)


class DetailCode(StrEnum):
    """`details[].code` — why one field was refused."""

    INVALID = "invalid"
    REQUIRED = "required"
    OUT_OF_BOUNDS = "out_of_bounds"
