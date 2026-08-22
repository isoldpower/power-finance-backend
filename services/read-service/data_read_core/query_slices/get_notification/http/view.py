from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import GetNotificationQuery
from ..query_handler import GetNotificationQueryHandler
from ._presenters import present_one
from ._serializers import EnvelopedNotificationDetailSerializer


@extend_schema(
    operation_id="notifications_retrieve",
    summary="Get notification details",
    description="Retrieve a specific notification.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Notification ID",
        )
    ],
    responses={
        200: EnvelopedNotificationDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_notification(request, notification_id=None):
    logger = get_query_logger("get_notification")
    log_request_received(
        logger,
        "get_notification",
        id=notification_id,
        user_id=request.user.id,
    )

    fetched = await GetNotificationQueryHandler().handle(
        GetNotificationQuery(user_id=request.user.id, notification_id=notification_id)
    )
    log_request_served(
        logger,
        "get_notification",
        id=notification_id,
    )

    return ok(
        present_one(fetched.resource),
        {"cached": fetched.cached},
    )
