from enum import StrEnum

from rest_framework import status


class ErrorCode(StrEnum):
    BAD_REQUEST = "bad_request"
    VALIDATION_FAILED = "validation_failed"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"

    IDEMPOTENCY_KEY_REQUIRED = "idempotency_key_required"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    IDEMPOTENCY_KEY_IN_FLIGHT = "idempotency_key_in_flight"

    CURSOR_INVALID = "cursor_invalid"
    CURSOR_MISMATCH = "cursor_mismatch"

    CHAIN_CYCLE = "chain_cycle"
    CHAIN_UNKNOWN_REFERENCE = "chain_unknown_reference"
    CHAIN_TOO_LONG = "chain_too_long"

    WALLET_CLOSED = "wallet_closed"
    WALLET_NOT_EMPTY = "wallet_not_empty"
    GOAL_NOT_EMPTY = "goal_not_empty"
    ALREADY_DELETED = "already_deleted"

    ASSISTANT_UNAVAILABLE = "assistant_unavailable"
    SUBSCRIPTION_EXISTS = "subscription_exists"
    UNKNOWN_RESOLUTION = "unknown_resolution"
    ACTION_ALREADY_RESOLVED = "action_already_resolved"

    UNSUPPORTED_CURRENCY = "unsupported_currency"
    RATE_UNAVAILABLE = "rate_unavailable"

    SERVICE_UNAVAILABLE = "service_unavailable"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CONFLICT = "conflict"

    @classmethod
    def from_wire(cls, wire_code: str | None) -> "ErrorCode | None":
        """The member a framework exception declared, if it names one of ours."""

        if wire_code is None:
            return None

        try:
            return cls(wire_code)
        except ValueError:
            return None


class DetailCode(StrEnum):
    REQUIRED = "required"
    UNKNOWN_FIELD = "unknown_field"

    AMOUNT_MALFORMED = "amount_malformed"
    AMOUNT_PRECISION = "amount_precision"
    AMOUNT_OUT_OF_RANGE = "amount_out_of_range"
    CURRENCY_MISMATCH = "currency_mismatch"

    NOT_A_REFERENCE = "not_a_reference"
    OUT_OF_BOUNDS = "out_of_bounds"

    TRIGGER_FIELD_CONFLICT = "trigger_field_conflict"
    EFFECT_UNKNOWN_TYPE = "effect_unknown_type"
    EFFECT_PARAMS_INVALID = "effect_params_invalid"
    EFFECT_SUBJECT_MISMATCH = "effect_subject_mismatch"
    UNKNOWN_EVENT_TYPE = "unknown_event_type"
    URL_SCHEME = "url_scheme"

    FILTER_UNKNOWN_FIELD = "filter_unknown_field"
    FILTER_OPERATOR_NOT_ALLOWED = "filter_operator_not_allowed"
    FILTER_VALUE_TYPE = "filter_value_type"
    FILTER_MALFORMED_GROUP = "filter_malformed_group"
    FILTER_MALFORMED_NODE = "filter_malformed_node"

    INVALID = "invalid"


STATUS_FOR_ERROR_CODE: dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: status.HTTP_400_BAD_REQUEST,
    ErrorCode.VALIDATION_FAILED: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
    ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.IDEMPOTENCY_KEY_REQUIRED: status.HTTP_400_BAD_REQUEST,
    ErrorCode.IDEMPOTENCY_KEY_REUSE: status.HTTP_409_CONFLICT,
    ErrorCode.IDEMPOTENCY_KEY_IN_FLIGHT: status.HTTP_409_CONFLICT,
    ErrorCode.CURSOR_INVALID: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.CURSOR_MISMATCH: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.CHAIN_CYCLE: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.CHAIN_UNKNOWN_REFERENCE: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.CHAIN_TOO_LONG: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.WALLET_CLOSED: status.HTTP_409_CONFLICT,
    ErrorCode.WALLET_NOT_EMPTY: status.HTTP_409_CONFLICT,
    ErrorCode.GOAL_NOT_EMPTY: status.HTTP_409_CONFLICT,
    ErrorCode.ALREADY_DELETED: status.HTTP_404_NOT_FOUND,
    ErrorCode.ASSISTANT_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.SUBSCRIPTION_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.UNKNOWN_RESOLUTION: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.ACTION_ALREADY_RESOLVED: status.HTTP_409_CONFLICT,
    ErrorCode.UNSUPPORTED_CURRENCY: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.RATE_UNAVAILABLE: status.HTTP_409_CONFLICT,
    ErrorCode.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.INSUFFICIENT_FUNDS: status.HTTP_409_CONFLICT,
    ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
}
