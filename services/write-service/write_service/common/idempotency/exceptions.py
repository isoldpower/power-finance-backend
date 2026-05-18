"""HTTP-mapped exceptions for the idempotency layer.

These extend DRF's `APIException` so the framework's exception handler turns
them into proper responses without any view-level translation.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException


class IdempotencyError(APIException):
    """Base class for all idempotency-related failures."""


class IdempotencyKeyRequired(IdempotencyError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "idempotency_key_required"
    default_detail = (
        "This endpoint requires an Idempotency-Key header to safely retry " "money-moving requests."
    )


class IdempotencyInFlight(IdempotencyError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "idempotency_in_flight"
    default_detail = "A request with the same Idempotency-Key is already being processed."


class IdempotencyKeyReused(IdempotencyError):
    """Same key, different request payload — Stripe-style 422."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "idempotency_key_reused"
    default_detail = (
        "Idempotency-Key has already been used for a different request. "
        "Reusing a key requires an identical body, method, and path."
    )


class IdempotencyUnavailable(IdempotencyError):
    """Redis unreachable on a money endpoint. Fail-closed."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "idempotency_unavailable"
    default_detail = (
        "Idempotency store unavailable. Refusing to process a money-moving "
        "request without dedup guarantees."
    )
