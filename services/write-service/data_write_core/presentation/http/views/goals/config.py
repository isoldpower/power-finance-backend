from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

GOAL_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Goal ID",
)
