from rest_framework import status
from rest_framework.exceptions import APIException

from write_service.common.http_contract import ErrorCode


class StoreUnavailable(RuntimeError):
    """Raised when Redis is unreachable; the caller decides fail-open vs fail-closed."""


class IdempotencyError(APIException):
    """Base class for all idempotency-related failures."""


class IdempotencyKeyRequired(IdempotencyError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.IDEMPOTENCY_KEY_REQUIRED
    default_detail = (
        "This endpoint requires an Idempotency-Key header to safely retry " "money-moving requests."
    )


class IdempotencyInFlight(IdempotencyError):
    status_code = status.HTTP_409_CONFLICT
    default_code = ErrorCode.IDEMPOTENCY_KEY_IN_FLIGHT
    default_detail = "A request with the same Idempotency-Key is already being processed."


class IdempotencyKeyReused(IdempotencyError):
    status_code = status.HTTP_409_CONFLICT
    default_code = ErrorCode.IDEMPOTENCY_KEY_REUSE
    default_detail = (
        "Idempotency-Key has already been used for a different request. "
        "Reusing a key requires an identical body, method, and path."
    )


class IdempotencyUnavailable(IdempotencyError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_detail = (
        "Idempotency store unavailable. Refusing to process a money-moving "
        "request without dedup guarantees."
    )
