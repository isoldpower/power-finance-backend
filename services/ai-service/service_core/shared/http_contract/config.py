from enum import StrEnum
from typing import Any

from .codes import ErrorCode
from .schemas import ErrorResponseSchema


class HeaderName(StrEnum):
    CORRELATION = "X-Correlation-ID"


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    ErrorCode.UNAUTHORIZED.status_code: {
        "model": ErrorResponseSchema,
        "description": "Did not traverse the API gateway.",
    },
    ErrorCode.VALIDATION_FAILED.status_code: {
        "model": ErrorResponseSchema,
        "description": "A parameter was refused.",
    },
}
