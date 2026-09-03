from dataclasses import dataclass

from .codes import DetailCode, ErrorCode


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    field: str
    code: DetailCode
    message: str

    def as_dict(self) -> dict:
        return {"field": self.field, "code": str(self.code), "message": self.message}


class ApiError(Exception):
    """A failure already shaped like the error envelope.

    Carrying the code rather than the status is what keeps the two from
    drifting: the status is derived from the code, in one place.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: tuple[ErrorDetail, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class Unauthorized(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.UNAUTHORIZED, message)


class ValidationFailed(ApiError):
    def __init__(
        self,
        message: str = "Request failed validation",
        details: tuple[ErrorDetail, ...] = (),
        code: ErrorCode = ErrorCode.VALIDATION_FAILED,
    ) -> None:
        super().__init__(code, message, details)
