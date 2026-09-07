from enum import StrEnum
from http import HTTPStatus


class ErrorCode(StrEnum):
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
    INVALID = "invalid"
    REQUIRED = "required"
    OUT_OF_BOUNDS = "out_of_bounds"
