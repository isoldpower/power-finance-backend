from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CREATED_AT_DESC, PageRequest, build_page
from data_read_core.shared.postgres_orm import Severity
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import ListNotificationsQuery
from ..query_handler import ListNotificationsQueryHandler
from ._filters import read_filters
from ._presenters import present_many
from ._serializers import PaginatedNotificationPreviewSerializer

ACKNOWLEDGED_PARAMETER = OpenApiParameter(
    "acknowledged",
    type=OpenApiTypes.BOOL,
    location=OpenApiParameter.QUERY,
    description=(
        "Restrict to read or unread. ABSENT means both — it is a tristate, not "
        "a boolean defaulting to either value."
    ),
)

SEVERITY_PARAMETER = OpenApiParameter(
    "severity",
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=list(Severity),
    description="Restrict to one severity. Absent means all of them.",
)


@extend_schema(
    operation_id="notifications_list",
    summary="List notifications",
    description=(
        "Retrieve a page of your notifications, newest first.\n\n"
        "Ordering is the global default — `created_at DESC, id DESC`. Unlike "
        "the actions queue this is a feed to be read rather than a list to be "
        "worked through, so a `critical` notification from Tuesday does NOT "
        "outrank an `info` from this morning."
    ),
    parameters=[
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
        ACKNOWLEDGED_PARAMETER,
        SEVERITY_PARAMETER,
    ],
    responses={
        200: PaginatedNotificationPreviewSerializer,
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

    filters_list = read_filters(request)
    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filters_list.as_cache_material(),
    )
    fetched = await ListNotificationsQueryHandler().handle(
        ListNotificationsQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters_list,
        )
    )

    notifications_page = build_page(
        fetched.rows,
        fetched.total,
        page_request,
    )
    log_request_served(
        logger,
        "list_notifications",
        user_id=request.user.id,
        total=notifications_page.total,
    )

    return ok(
        present_many(notifications_page.items),
        notifications_page.meta(cached=fetched.cached),
    )
