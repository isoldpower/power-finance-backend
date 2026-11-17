from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

CATEGORY_ID_PARAMETER = OpenApiParameter(
    "category_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Category ID",
)
