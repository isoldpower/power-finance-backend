from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)
from data_read_core.shared.postgres_orm import Severity

from ..dtos import NotificationFilters

# The query-param spellings. They live here rather than beside the dataclass
# because they name what a REQUEST calls these, which is HTTP's business.
ACKNOWLEDGED_PARAM = "acknowledged"
SEVERITY_PARAM = "severity"

TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}

NOT_A_BOOLEAN_MESSAGE = "{parameter} must be a boolean ({legal})."
UNKNOWN_SEVERITY_MESSAGE = "Unknown severity. Legal values: {legal}."


def read_filters(request: Request) -> NotificationFilters:
    return NotificationFilters(
        acknowledged=_read_acknowledged(
            request.query_params.get(ACKNOWLEDGED_PARAM),
        ),
        severity=_read_severity(
            request.query_params.get(SEVERITY_PARAM),
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
                field=ACKNOWLEDGED_PARAM,
                code=DetailCode.INVALID,
                message=NOT_A_BOOLEAN_MESSAGE.format(
                    parameter=ACKNOWLEDGED_PARAM,
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
                field=SEVERITY_PARAM,
                code=DetailCode.INVALID,
                message=UNKNOWN_SEVERITY_MESSAGE.format(legal=", ".join(Severity)),
            )
        ]
    )
