from enum import IntEnum, StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from data_read_core.shared.postgres_orm import Severity


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class ParamsList(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    SEVERITY = "severity"


class Messages(StrEnum):
    NOT_A_BOOLEAN = "{parameter} must be a boolean ({legal})."
    UNKNOWN_SEVERITY = "Unknown severity. Legal values: {legal}."


TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}


ACKNOWLEDGED_PARAMETER = OpenApiParameter(
    ParamsList.ACKNOWLEDGED,
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description=(
        "Restrict to read or unread. ABSENT means both — it is a tristate, not "
        "a boolean defaulting to either value."
    ),
)

SEVERITY_PARAMETER = OpenApiParameter(
    ParamsList.SEVERITY,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=list(Severity),
    description="Restrict to one severity. Absent means all of them.",
)
