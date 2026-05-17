from rest_framework.permissions import IsAuthenticated
from write_service.common.base_async_api_view import BaseAsyncAPIView

from ...pagination import StandardResultsPagination


class WalletView(BaseAsyncAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination
