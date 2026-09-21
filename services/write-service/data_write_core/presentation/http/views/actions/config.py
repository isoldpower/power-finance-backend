from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

ACTION_ID_PARAMETER = OpenApiParameter(
    "action_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Action ID",
)
