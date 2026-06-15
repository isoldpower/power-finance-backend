from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.logging import (
    get_query_logger,
    log_request_failed,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    StandardResultsPagination,
    async_api_view,
)

from ..dtos import ListNotificationsQuery
from ..query_handler import ListNotificationsQueryHandler
from ._presenters import present_many
from ._serializers import (
    MessageResponseSerializer,
    PaginatedNotificationResponseSerializer,
)


@extend_schema(
    operation_id="notifications_list",
    summary="List notifications",
    description="Retrieve a paginated list of your notifications, newest first.",
    parameters=[
        OpenApiParameter(
            "limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Maximum number of notifications to return.",
        ),
        OpenApiParameter(
            "offset",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of notifications to skip.",
        ),
        OpenApiParameter(
            "only_unread",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Return only unacknowledged notifications.",
        ),
    ],
    responses={
        200: PaginatedNotificationResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_notifications(request):
    logger = get_query_logger("list_notifications")

    try:
        log_request_received(logger, "list_notifications", user_id=request.user.id)

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)
        only_unread = request.query_params.get("only_unread") in ("1", "true", "True")

        notifications, total = await ListNotificationsQueryHandler().handle(
            ListNotificationsQuery(
                user_id=request.user.id,
                limit=paginator.limit,
                offset=paginator.offset,
                filters={"only_unread": only_unread} if only_unread else {},
            )
        )

        paginator.count = total
        log_request_served(logger, "list_notifications", user_id=request.user.id, total=total)

        payload = present_many(notifications)
        return paginator.get_paginated_response(payload)
    except Exception as error:
        log_request_failed(logger, "list_notifications", error, user_id=request.user.id)
        payload = {
            "message": f"Failed to list owned notifications: {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
