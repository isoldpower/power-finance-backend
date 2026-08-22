from rest_framework.request import Request
from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed
from write_service.common.timestamps import DEFAULT_PERIOD, Period

PERIOD_PARAM = "period"

UNKNOWN_PERIOD_MESSAGE = "Unknown period. Legal values: {legal}."


def resolve_period(request: Request) -> Period:
    """Mirrors the read side exactly. The gateway can reroute mid-session, so a
    request that asked for a window has to get that window here too."""

    raw_period = request.query_params.get(PERIOD_PARAM)
    if not raw_period:
        return DEFAULT_PERIOD

    try:
        return Period(raw_period.strip().lower())
    except ValueError:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field=PERIOD_PARAM,
                    code=DetailCode.INVALID,
                    message=UNKNOWN_PERIOD_MESSAGE.format(
                        legal=", ".join(period.value for period in Period)
                    ),
                )
            ]
        ) from None
