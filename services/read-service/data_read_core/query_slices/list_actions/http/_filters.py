from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.postgres_orm import ActionSeverity, ActionSource, ActionStatus

from ..dtos import ActionFilters, Param

UNKNOWN_VALUE_MESSAGE = "Unknown {parameter}. Legal values: {legal}."


def read_filters(request: Request) -> ActionFilters:
    return ActionFilters(
        status=_read_choice(
            request.query_params.get(Param.STATUS_PARAM),
            Param.STATUS_PARAM,
            ActionStatus,
            default=ActionStatus.PENDING,
        ),
        source=_read_choice(
            request.query_params.get(Param.SOURCE_PARAM),
            Param.SOURCE_PARAM,
            ActionSource,
        ),
        severity=_read_choice(
            request.query_params.get(Param.SEVERITY_PARAM),
            Param.SEVERITY_PARAM,
            ActionSeverity,
        ),
    )


def _read_choice(
    raw: str | None,
    parameter: str,
    vocabulary,
    default: str | None = None,
):
    if not raw:
        return default

    candidate = raw.strip().lower()
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
