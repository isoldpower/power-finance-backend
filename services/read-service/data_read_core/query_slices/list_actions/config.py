from enum import IntEnum, StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from data_read_core.shared.postgres_orm import ActionSeverity, ActionSource, ActionStatus


class CacheSettings(IntEnum):
    TTL_SECONDS = 60


class CacheSchema(StrEnum):
    VERSION = "s1"


class ParamsList(StrEnum):
    STATUS = "status"
    SOURCE = "source"
    SEVERITY = "severity"


class Messages(StrEnum):
    UNKNOWN_VALUE = "Unknown {parameter}. Legal values: {legal}."


class ResolutionIntent(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"


RESOLUTION_INTENTS = tuple(str(intent) for intent in ResolutionIntent)

STATUS_PARAMETER = OpenApiParameter(
    ParamsList.STATUS,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionStatus],
    description="Which queue state to list. Defaults to `pending`.",
)
SOURCE_PARAMETER = OpenApiParameter(
    ParamsList.SOURCE,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionSource],
    description="Restrict to one producer. Absent means both.",
)
SEVERITY_PARAMETER = OpenApiParameter(
    ParamsList.SEVERITY,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[member.value for member in ActionSeverity],
    description="Restrict to one severity. Absent means all of them.",
)
