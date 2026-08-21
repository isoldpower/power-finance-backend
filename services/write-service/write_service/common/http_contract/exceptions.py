from dataclasses import dataclass
from typing import Any

from .codes import STATUS_FOR_ERROR_CODE, DetailCode, ErrorCode


@dataclass(frozen=True)
class ErrorDetail:
    """One field-level failure inside `error.details`."""

    field: str | None
    code: DetailCode
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "code": str(self.code),
            "message": self.message,
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
        self.status_code = status_code or STATUS_FOR_ERROR_CODE[self.code]

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
    code = ErrorCode.NOT_FOUND
    message = "Resource does not exist"


class Conflict(ApiError):
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
