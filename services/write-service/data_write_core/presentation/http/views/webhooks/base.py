from write_service.common.base_async_api_view import BaseAsyncAPIView

from ...auth import IsGatewayAuthenticated


class WebhookView(BaseAsyncAPIView):
    permission_classes = [IsGatewayAuthenticated]
