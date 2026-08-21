from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

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


def resource_id_parameter(name: str, description: str) -> OpenApiParameter:
    return OpenApiParameter(
        name,
        type=OpenApiTypes.UUID,
        location=OpenApiParameter.PATH,
        description=description,
    )
