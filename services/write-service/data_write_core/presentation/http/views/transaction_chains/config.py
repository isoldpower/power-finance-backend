from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

CHAIN_ID_PARAMETER = OpenApiParameter(
    "chain_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Chain ID",
)

TRANSACTIONS_NAMESPACE = "transactions"
