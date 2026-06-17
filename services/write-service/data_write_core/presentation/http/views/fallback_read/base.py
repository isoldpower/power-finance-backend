from write_service.common.base_async_api_view import BaseAsyncAPIView

from ...gateway_authentication import IsGatewayAuthenticated
from ...pagination import StandardResultsPagination


class FallbackReadView(BaseAsyncAPIView):
    """Base for the always-consistent fallback-read routes."""

    permission_classes = [IsGatewayAuthenticated]
    pagination_class = StandardResultsPagination
