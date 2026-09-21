from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)

from ..config import FALSE_STATEMENTS, TRUTH_STATEMENTS, Messages, ParamsList
from ..dtos import WebhookFilters


def read_filters(request: Request) -> WebhookFilters:
    return WebhookFilters(
        enabled=_read_enabled(request.query_params.get(ParamsList.ENABLED)),
    )


def _read_enabled(raw_enabled: str | None) -> bool | None:
    if raw_enabled is None:
        return None

    candidate = raw_enabled.strip().lower()
    if candidate in TRUTH_STATEMENTS:
        return True
    if candidate in FALSE_STATEMENTS:
        return False

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=ParamsList.ENABLED,
                code=DetailCode.INVALID,
                message=Messages.NOT_A_BOOLEAN.format(
                    parameter=ParamsList.ENABLED,
                    legal=", ".join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS)),
                ),
            )
        ]
    )
