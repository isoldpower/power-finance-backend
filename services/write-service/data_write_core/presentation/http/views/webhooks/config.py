from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

SUBSCRIPTION_ID_PARAMETER = OpenApiParameter(
    "subscription_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Subscription ID",
)

WEBHOOK_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Webhook ID",
)
