from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from write_service.common.timestamps import DEFAULT_PERIOD, Period

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


PERIOD_PARAMETER = OpenApiParameter(
    "period",
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


def resource_id_parameter(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(
        name,
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.PATH,
        description=description,
    )
