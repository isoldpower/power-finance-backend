from enum import IntEnum, StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


class CacheSettings(IntEnum):
    TTL_SECONDS = 120


class CacheSchema(StrEnum):
    VERSION = "s1"


class ParamsList(StrEnum):
    ENABLED = "enabled"


TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}


ENABLED_PARAMETER = OpenApiParameter(
    ParamsList.ENABLED,
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description="Restrict to enabled or disabled. ABSENT means both.",
)
