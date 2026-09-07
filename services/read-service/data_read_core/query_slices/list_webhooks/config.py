from enum import IntEnum, StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class ParamsList(StrEnum):
    ENABLED = "enabled"


class Messages(StrEnum):
    NOT_A_BOOLEAN = "{parameter} must be a boolean ({legal})."


TRUTH_STATEMENTS = {"1", "true", "yes", "on"}
FALSE_STATEMENTS = {"0", "false", "no", "off"}


ENABLED_PARAMETER = OpenApiParameter(
    ParamsList.ENABLED,
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description=(
        "Restrict to enabled or disabled endpoints. ABSENT means both — it is "
        "a tristate, not a boolean defaulting to either value."
    ),
)
