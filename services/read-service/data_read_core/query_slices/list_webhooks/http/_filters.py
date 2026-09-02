from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)

from ..dtos import WebhookFilters

ENABLED_PARAM = "enabled"
TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}
NOT_A_BOOLEAN_MESSAGE = "{parameter} must be a boolean ({legal})."


def read_filters(request: Request) -> WebhookFilters:
    return WebhookFilters(
        enabled=_read_enabled(request.query_params.get(ENABLED_PARAM)),
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
                field=ENABLED_PARAM,
                code=DetailCode.INVALID,
                message=NOT_A_BOOLEAN_MESSAGE.format(
                    parameter=ENABLED_PARAM,
                    legal=", ".join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS)),
                ),
            )
        ]
    )
