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

from ..dtos import ListNotificationsQuery
from ..query_handler import ListNotificationsQueryHandler
from ._presenters import present_many
from ._serializers import PaginatedNotificationResponseSerializer

ONLY_UNREAD_PARAMETER = OpenApiParameter(
    "only_unread",
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description="Return only unacknowledged notifications.",
)


@extend_schema(
    operation_id="notifications_list",
    summary="List notifications",
    description="Retrieve a page of your notifications, newest first.",
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER, ONLY_UNREAD_PARAMETER],
    responses={
        200: PaginatedNotificationResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_notifications(request):
    logger = get_query_logger("list_notifications")
    log_request_received(
        logger,
        "list_notifications",
        user_id=request.user.id,
    )

    only_unread = request.query_params.get("only_unread") in ("1", "true", "True")
    filters = {"only_unread": only_unread} if only_unread else {}

    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filters,
    )
    fetched = await ListNotificationsQueryHandler().handle(
        ListNotificationsQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters,
        )
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_notifications",
        user_id=request.user.id,
        total=page.total,
    )

    return ok(
        present_many(page.items),
        page.meta(cached=fetched.cached),
    )
