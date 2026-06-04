from write_service.common.base_async_api_view import BaseAsyncAPIView

from ...gateway_authentication import IsGatewayAuthenticated
from ...pagination import StandardResultsPagination


class FallbackReadView(BaseAsyncAPIView):
    """Base for the always-consistent fallback-read routes.

    The gateway redirects here when the Read Service answers 507 (its projection
    has not caught up to the client's ``Read-At-Least``). These reads hit the
    write side's source of truth (Postgres wallets + ImmuDB ledger), so they are
    slower but never stale.
    """

    permission_classes = [IsGatewayAuthenticated]
    pagination_class = StandardResultsPagination
