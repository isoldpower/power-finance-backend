from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

AUTOMATION_ID_PARAMETER = OpenApiParameter(
    "automation_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Automation ID",
)
