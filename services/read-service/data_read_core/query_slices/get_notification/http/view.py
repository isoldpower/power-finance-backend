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
from data_read_core.shared.rest_framework import async_api_view

from ..dtos import GetNotificationQuery
from ..exceptions import NotificationNotFoundError
from ..query_handler import GetNotificationQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, NotificationResponseSerializer


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
        200: NotificationResponseSerializer,
        400: MessageResponseSerializer,
        404: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_notification(request, pk=None):
    logger = get_query_logger("get_notification")

    try:
        log_request_received(logger, "get_notification", id=pk, user_id=request.user.id)

        retrieved_notification = await GetNotificationQueryHandler().handle(
            GetNotificationQuery(
                user_id=request.user.id,
                notification_id=pk,
            )
        )
        payload = present_one(retrieved_notification)
        log_request_served(logger, "get_notification", id=pk)

        return Response(payload, status=status.HTTP_200_OK)
    except NotificationNotFoundError:
        logger.info(
            "get_notification: notification not found (id=%s, user_id=%s)",
            pk,
            request.user.id,
        )
        payload = {
            "message": f"Notification with ID {pk} not found.",
            "resource_id": f"{pk}",
        }
        return Response(payload, status=status.HTTP_404_NOT_FOUND)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve notification with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        log_request_failed(logger, "get_notification", error, id=pk, user_id=request.user.id)

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
