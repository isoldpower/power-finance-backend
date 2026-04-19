from rest_framework import status
from rest_framework.exceptions import APIException


class IdempotencyInFlightError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A request with this Idempotency-Key is already being processed."
    default_code = "idempotency_in_flight"


class IdempotencyKeyMissingError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Idempotency-Key header is required for this operation."
    default_code = "idempotency_key_missing"
