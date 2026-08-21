from dataclasses import dataclass
from typing import Any

from .codes import DetailCode, ErrorCode

FIELD_KEY = "field"
CODE_KEY = "code"
MESSAGE_KEY = "message"


@dataclass(frozen=True)
class ErrorDetail:
    """One field-level failure in `error.details`, `field` being a JSON path."""

    field: str | None
    code: DetailCode
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            FIELD_KEY: self.field,
            CODE_KEY: str(self.code),
            MESSAGE_KEY: self.message,
        }


class ApiError(Exception):
    """Base class for every failure that maps onto the error envelope."""

    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    message: str = "Unexpected server failure"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: ErrorCode | None = None,
        details: list[ErrorDetail] | None = None,
        status_code: int | None = None,
    ) -> None:
        self.code = code or self.code
        self.message = message or self.message
        self.details = details
        self.status_code = status_code or self.code.status_code
        super().__init__(self.message)


class BadRequest(ApiError):
    code = ErrorCode.BAD_REQUEST
    message = "Request is malformed"


class ValidationFailed(ApiError):
    code = ErrorCode.VALIDATION_FAILED
    message = "Request body failed validation"


class Unauthorized(ApiError):
    code = ErrorCode.UNAUTHORIZED
    message = "Authentication credentials are missing or invalid"


class Forbidden(ApiError):
    code = ErrorCode.FORBIDDEN
    message = "This action is not permitted on that resource"


class NotFound(ApiError):
    """404 also covers "belongs to another user": 403 would make every UUID path
    an existence oracle."""

    code = ErrorCode.NOT_FOUND
    message = "Resource does not exist"


class Conflict(ApiError):
    """409: the request can succeed once state changes, where 422 never will."""

    code = ErrorCode.CONFLICT
    message = "Request conflicts with the current server state"


class ServiceUnavailable(ApiError):
    code = ErrorCode.SERVICE_UNAVAILABLE
    message = "A dependency of this endpoint is temporarily unreachable"


class CursorInvalid(ValidationFailed):
    code = ErrorCode.CURSOR_INVALID
    message = "Pagination cursor is malformed or unreadable"


class CursorMismatch(ValidationFailed):
    code = ErrorCode.CURSOR_MISMATCH
    message = "Pagination cursor does not match the query it was sent with"


class UnsupportedCurrency(ValidationFailed):
    code = ErrorCode.UNSUPPORTED_CURRENCY
    message = "Currency is not supported"
