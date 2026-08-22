from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.timestamps import DEFAULT_PERIOD, Period

PERIOD_PARAM = "period"
"""One name for three things that must agree: the query param, the `details[].field`
of a rejection, and the `meta` key the choice is echoed under."""

UNKNOWN_PERIOD_MESSAGE = "Unknown period. Legal values: {legal}."


def resolve_period(request: Request) -> Period:
    """`?period=` selects the reporting window; absent means `last_month`.

    An unknown value is a 422 rather than a silent fall back to the default. The
    caller asked for figures over a window, and quietly answering about a
    different one is worse than refusing — unlike the PREFERENCE headers, which
    degrade quietly because the client never asked for them.
    """

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
