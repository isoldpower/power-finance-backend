from rest_framework.request import Request
from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed
from write_service.common.timestamps import DEFAULT_PERIOD, Period

PERIOD_PARAM = "period"
TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}
UNKNOWN_PERIOD_MESSAGE = "Unknown period. Legal values: {legal}."
NOT_A_BOOLEAN_MESSAGE = "{parameter} must be a boolean ({legal})."


def resolve_tristate_flag(request: Request, parameter: str) -> bool | None:
    raw_value = request.query_params.get(parameter)
    if raw_value is None:
        return None

    candidate = raw_value.strip().lower()
    if candidate in TRUTH_STATEMENTS:
        return True
    if candidate in FALSE_STATEMENTS:
        return False

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=parameter,
                code=DetailCode.INVALID,
                message=NOT_A_BOOLEAN_MESSAGE.format(
                    parameter=parameter,
                    legal=", ".join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS)),
                ),
            )
        ]
    )


def resolve_period(request: Request) -> Period:
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
