from enum import StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from write_service.common.timestamps import DEFAULT_PERIOD, Period

from data_write_core.domain.entities import ActionSeverity, ActionSource, ActionStatus


class ParamsList(StrEnum):
    PERIOD = "period"


class Messages(StrEnum):
    UNKNOWN_PERIOD = "Unknown period. Legal values: {legal}."
    UNKNOWN_VALUE = "Unknown {parameter}. Legal values: {legal}."
    NOT_A_BOOLEAN = "{parameter} must be a boolean ({legal})."


TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}

LIMIT_PARAMETER = OpenApiParameter(
    "limit",
    type=OpenApiTypes.INT,
    location=OpenApiParameter.QUERY,
    description="Page size. Defaults to 25, clamped to 1..100.",
)

CURSOR_PARAMETER = OpenApiParameter(
    "cursor",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    description="Opaque cursor from a previous response's `meta.next_cursor` or `meta.prev_cursor`.",
)


ENABLED_PARAMETER = OpenApiParameter(
    "enabled",
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description=(
        "Restrict to enabled or disabled endpoints. ABSENT means both — it is "
        "a tristate, not a boolean defaulting to either value."
    ),
)


STATUS_PARAMETER = OpenApiParameter(
    "status",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionStatus],
    description="Which queue state to list. Defaults to `pending`.",
)


SOURCE_PARAMETER = OpenApiParameter(
    "source",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionSource],
    description="Restrict to one producer. Absent means both.",
)


SEVERITY_PARAMETER = OpenApiParameter(
    "severity",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionSeverity],
    description="Restrict to one severity. Absent means all of them.",
)


PERIOD_PARAMETER = OpenApiParameter(
    "period",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[period.value for period in Period],
    default=DEFAULT_PERIOD.value,
    description=(
        "Window for the `period` inflow/outflow figures. Every value is a "
        "ROLLING window of whole days ending with today, resolved in your "
        "timezone preference: `last_week` is the last 7 days, `last_month` "
        "the last 30, `last_year` the last 365. Today is included."
    ),
)


def resource_id_parameter(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(
        name,
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.PATH,
        description=description,
    )


WEBHOOK_ID_PARAMETER = resource_id_parameter("id", "Webhook ID")
