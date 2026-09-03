from enum import StrEnum

from rest_framework.request import Request
from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed
from write_service.common.timestamps import DEFAULT_PERIOD, Period

PERIOD_PARAM = "period"
TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}
UNKNOWN_PERIOD_MESSAGE = "Unknown period. Legal values: {legal}."
UNKNOWN_VALUE_MESSAGE = "Unknown {parameter}. Legal values: {legal}."
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


def resolve_choice(
    request: Request,
    parameter: str,
    vocabulary: type[StrEnum],
) -> str | None:
    """An optional filter: absent means "every value"."""

    return _read_choice(request, parameter, vocabulary) or None


def resolve_choice_or(
    request: Request,
    parameter: str,
    vocabulary: type[StrEnum],
    default: str,
) -> str:
    """A filter with a default, which therefore always resolves to a value."""

    return _read_choice(request, parameter, vocabulary) or default


def _read_choice(
    request: Request,
    parameter: str,
    vocabulary: type[StrEnum],
) -> str | None:
    """The read side's `_read_choice`, word for word — including the message, so
    a rejected filter reads the same whichever side answered the request."""

    raw_value = request.query_params.get(parameter)
    if not raw_value:
        return None

    candidate = raw_value.strip().lower()
    if candidate in list(vocabulary):
        return candidate

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=parameter,
                code=DetailCode.INVALID,
                message=UNKNOWN_VALUE_MESSAGE.format(
                    parameter=parameter,
                    legal=", ".join(member.value for member in vocabulary),
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
