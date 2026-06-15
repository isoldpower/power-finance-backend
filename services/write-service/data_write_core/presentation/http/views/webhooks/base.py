from write_service.common.base_async_api_view import BaseAsyncAPIView

from ...gateway_authentication import IsGatewayAuthenticated
from ...pagination import StandardResultsPagination


class WebhookView(BaseAsyncAPIView):
    permission_classes = [IsGatewayAuthenticated]
    pagination_class = StandardResultsPagination
