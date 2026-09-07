from enum import StrEnum

from rest_framework.request import Request
from write_service.common.http_contract import DetailCode, ErrorDetail, ValidationFailed
from write_service.common.timestamps import DEFAULT_PERIOD, Period

from .config import FALSE_STATEMENTS, TRUTH_STATEMENTS, Messages, ParamsList


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
                message=Messages.NOT_A_BOOLEAN.format(
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
    return _read_choice(request, parameter, vocabulary) or None


def resolve_choice_or(
    request: Request,
    parameter: str,
    vocabulary: type[StrEnum],
    default: str,
) -> str:
    return _read_choice(request, parameter, vocabulary) or default


def _read_choice(
    request: Request,
    parameter: str,
    vocabulary: type[StrEnum],
) -> str | None:
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
                message=Messages.UNKNOWN_VALUE.format(
                    parameter=parameter,
                    legal=", ".join(member.value for member in vocabulary),
                ),
            )
        ]
    )


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
