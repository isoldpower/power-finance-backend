from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CREATED_AT_DESC, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import ListWebhooksQuery
from ..query_handler import ListWebhooksQueryHandler
from ._filters import read_filters
from ._presenters import present_many
from ._serializers import PaginatedWebhookPreviewSerializer

ENABLED_PARAMETER = OpenApiParameter(
    "enabled",
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description=(
        "Restrict to enabled or disabled endpoints. ABSENT means both — it is "
        "a tristate, not a boolean defaulting to either value."
    ),
)


@extend_schema(
    operation_id="webhooks_list",
    summary="List webhooks",
    description="Retrieve a page of your webhook endpoints, newest first.",
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER, ENABLED_PARAMETER],
    responses={
        200: PaginatedWebhookPreviewSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_webhooks(request):
    logger = get_query_logger("list_webhooks")
    log_request_received(
        logger,
        "list_webhooks",
        user_id=request.user.id,
    )

    filters = read_filters(request)
    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filters.as_cache_material(),
    )
    fetched = await ListWebhooksQueryHandler().handle(
        ListWebhooksQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters,
        )
    )

    webhooks_page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_webhooks",
        user_id=request.user.id,
        total=webhooks_page.total,
    )

    return ok(
        present_many(webhooks_page.items),
        webhooks_page.meta(cached=fetched.cached),
    )
