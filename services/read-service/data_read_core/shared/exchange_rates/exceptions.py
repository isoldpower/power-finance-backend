from data_read_core.shared.http_contract import ApiError, ErrorCode


class RateUnavailable(ApiError):
    """A supported currency with no rate we are willing to serve."""

    code = ErrorCode.RATE_UNAVAILABLE
    message = "No fresh exchange rate is available for this currency"
