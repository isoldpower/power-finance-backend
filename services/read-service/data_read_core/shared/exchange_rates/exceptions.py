from data_read_core.shared.http_contract import ApiError, ErrorCode


class RateUnavailable(ApiError):
    code = ErrorCode.RATE_UNAVAILABLE
    message = "No fresh exchange rate is available for this currency"
