from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.timestamps import DEFAULT_PERIOD, Period

from ..config import Messages, ParamsList


def resolve_period(request: Request) -> Period:
    raw_period = request.query_params.get(ParamsList.PERIOD)
    if not raw_period:
        return DEFAULT_PERIOD

    try:
        return Period(raw_period.strip().lower())
    except ValueError:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field=ParamsList.PERIOD,
                    code=DetailCode.INVALID,
                    message=Messages.UNKNOWN_PERIOD.format(
                        legal=", ".join(period.value for period in Period)
                    ),
                )
            ]
        ) from None
