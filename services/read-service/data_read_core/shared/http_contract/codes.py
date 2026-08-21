from enum import StrEnum

from rest_framework import status

LOWEST_SERVER_ERROR_STATUS = status.HTTP_500_INTERNAL_SERVER_ERROR


class ErrorCode(StrEnum):
    """Top-level `error.code`, each member carrying the status it is served with."""

    _status_code: int

    def __new__(cls, wire_code: str, status_code: int) -> "ErrorCode":
        member = str.__new__(cls, wire_code)
        member._value_ = wire_code
        member._status_code = status_code

        return member

    BAD_REQUEST = ("bad_request", status.HTTP_400_BAD_REQUEST)
    VALIDATION_FAILED = ("validation_failed", status.HTTP_422_UNPROCESSABLE_ENTITY)
    UNAUTHORIZED = ("unauthorized", status.HTTP_401_UNAUTHORIZED)
    FORBIDDEN = ("forbidden", status.HTTP_403_FORBIDDEN)
    NOT_FOUND = ("not_found", status.HTTP_404_NOT_FOUND)
    RATE_LIMITED = ("rate_limited", status.HTTP_429_TOO_MANY_REQUESTS)
    INTERNAL_ERROR = ("internal_error", status.HTTP_500_INTERNAL_SERVER_ERROR)

    IDEMPOTENCY_KEY_REQUIRED = ("idempotency_key_required", status.HTTP_400_BAD_REQUEST)
    IDEMPOTENCY_KEY_REUSE = ("idempotency_key_reuse", status.HTTP_409_CONFLICT)
    IDEMPOTENCY_KEY_IN_FLIGHT = ("idempotency_key_in_flight", status.HTTP_409_CONFLICT)

    CURSOR_INVALID = ("cursor_invalid", status.HTTP_422_UNPROCESSABLE_ENTITY)
    CURSOR_MISMATCH = ("cursor_mismatch", status.HTTP_422_UNPROCESSABLE_ENTITY)

    CHAIN_CYCLE = ("chain_cycle", status.HTTP_422_UNPROCESSABLE_ENTITY)
    CHAIN_UNKNOWN_REFERENCE = ("chain_unknown_reference", status.HTTP_422_UNPROCESSABLE_ENTITY)
    CHAIN_TOO_LONG = ("chain_too_long", status.HTTP_422_UNPROCESSABLE_ENTITY)

    WALLET_CLOSED = ("wallet_closed", status.HTTP_409_CONFLICT)
    WALLET_NOT_EMPTY = ("wallet_not_empty", status.HTTP_409_CONFLICT)
    GOAL_NOT_EMPTY = ("goal_not_empty", status.HTTP_409_CONFLICT)
    ALREADY_DELETED = ("already_deleted", status.HTTP_404_NOT_FOUND)

    ASSISTANT_UNAVAILABLE = ("assistant_unavailable", status.HTTP_503_SERVICE_UNAVAILABLE)
    SUBSCRIPTION_EXISTS = ("subscription_exists", status.HTTP_409_CONFLICT)
    UNKNOWN_RESOLUTION = ("unknown_resolution", status.HTTP_422_UNPROCESSABLE_ENTITY)
    ACTION_ALREADY_RESOLVED = ("action_already_resolved", status.HTTP_409_CONFLICT)

    UNSUPPORTED_CURRENCY = ("unsupported_currency", status.HTTP_422_UNPROCESSABLE_ENTITY)
    RATE_UNAVAILABLE = ("rate_unavailable", status.HTTP_409_CONFLICT)

    SERVICE_UNAVAILABLE = ("service_unavailable", status.HTTP_503_SERVICE_UNAVAILABLE)
    INSUFFICIENT_FUNDS = ("insufficient_funds", status.HTTP_409_CONFLICT)
    CONFLICT = ("conflict", status.HTTP_409_CONFLICT)

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def carries_details(self) -> bool:
        """Field-level details never ride along with a 500."""
        return self is not ErrorCode.INTERNAL_ERROR

    @classmethod
    def from_wire(cls, wire_code: str | None) -> "ErrorCode | None":
        """The member a framework exception declared, if it names one of ours."""
        if wire_code is None:
            return None

        return ERROR_CODE_BY_WIRE.get(wire_code)

    @classmethod
    def for_status(cls, status_code: int) -> "ErrorCode":
        """The code a failure gets when it arrives carrying only a status."""
        named = ERROR_CODE_BY_STATUS.get(status_code)
        if named is not None:
            return named

        if status_code >= LOWEST_SERVER_ERROR_STATUS:
            return cls.INTERNAL_ERROR

        return cls.BAD_REQUEST


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


ERROR_CODE_BY_WIRE: dict[str, ErrorCode] = {code.value: code for code in ErrorCode}

ERROR_CODE_BY_STATUS: dict[int, ErrorCode] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_FAILED,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMITED,
    status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
}
