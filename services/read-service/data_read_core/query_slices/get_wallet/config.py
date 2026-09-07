from enum import IntEnum, StrEnum

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

from data_read_core.shared.timestamps import DEFAULT_PERIOD, Period


class CacheSettings(IntEnum):
    TTL_SECONDS = 300


class CacheSchema(StrEnum):
    VERSION = "s2"


class ParamsList(StrEnum):
    PERIOD = "period"


class CacheNamespace(StrEnum):
    RECENT = "recent"


class Messages(StrEnum):
    UNKNOWN_PERIOD = "Unknown period. Legal values: {legal}."


PERIOD_PARAMETER = OpenApiParameter(
    ParamsList.PERIOD,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[period.value for period in Period],
    default=DEFAULT_PERIOD.value,
    description=(
        "Window for the `period` inflow/outflow figures. Every value is a "
        "CALENDAR window resolved in your timezone preference, not a rolling "
        "count of days."
    ),
)
