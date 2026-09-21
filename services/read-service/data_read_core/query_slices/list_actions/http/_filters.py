from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed
from data_read_core.shared.postgres_orm import ActionSeverity, ActionSource, ActionStatus

from ..config import Messages, ParamsList
from ..dtos import ActionFilters


def read_filters(request: Request) -> ActionFilters:
    return ActionFilters(
        status=_read_choice(
            request.query_params.get(ParamsList.STATUS),
            ParamsList.STATUS,
            ActionStatus,
            default=ActionStatus.PENDING,
        ),
        source=_read_choice(
            request.query_params.get(ParamsList.SOURCE),
            ParamsList.SOURCE,
            ActionSource,
        ),
        severity=_read_choice(
            request.query_params.get(ParamsList.SEVERITY),
            ParamsList.SEVERITY,
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
                message=Messages.UNKNOWN_VALUE.format(
                    parameter=parameter,
                    legal=", ".join(member.value for member in vocabulary),
                ),
            )
        ]
    )
