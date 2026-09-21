from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)
from data_read_core.shared.postgres_orm import Severity

from ..config import FALSE_STATEMENTS, TRUTH_STATEMENTS, Messages, ParamsList
from ..dtos import NotificationFilters


def read_filters(request: Request) -> NotificationFilters:
    return NotificationFilters(
        acknowledged=_read_acknowledged(
            request.query_params.get(ParamsList.ACKNOWLEDGED),
        ),
        severity=_read_severity(
            request.query_params.get(ParamsList.SEVERITY),
        ),
    )


def _read_acknowledged(raw_acknowledged: str | None) -> bool | None:
    if raw_acknowledged is None:
        return None

    candidate = raw_acknowledged.strip().lower()
    if candidate in TRUTH_STATEMENTS:
        return True
    if candidate in FALSE_STATEMENTS:
        return False

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=ParamsList.ACKNOWLEDGED,
                code=DetailCode.INVALID,
                message=Messages.NOT_A_BOOLEAN.format(
                    parameter=ParamsList.ACKNOWLEDGED,
                    legal=", ".join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS)),
                ),
            )
        ]
    )


def _read_severity(raw: str | None) -> str | None:
    if not raw:
        return None

    candidate = raw.strip().lower()
    if candidate in list(Severity):
        return candidate

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=ParamsList.SEVERITY,
                code=DetailCode.INVALID,
                message=Messages.UNKNOWN_SEVERITY.format(legal=", ".join(Severity)),
            )
        ]
    )
