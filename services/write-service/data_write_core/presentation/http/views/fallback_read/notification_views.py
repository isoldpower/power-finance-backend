from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.queries import (
    GetFallbackNotificationQuery,
    GetFallbackNotificationQueryHandler,
    ListFallbackNotificationsQuery,
    ListFallbackNotificationsQueryHandler,
)
from data_write_core.domain.exceptions import NotificationNotFoundError

from ...decorators import trace_handler_flow
from ._presenters import present_notification, present_notifications
from .base import FallbackReadView

logger = get_http_logger("fallback_read")


class FallbackNotificationListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_notifications_list",
        summary="List notifications (consistent fallback)",
        description=(
            "Always-consistent notification list served from the write side. "
            "The gateway routes here when the Read Service is not caught up."
        ),
        parameters=[
            OpenApiParameter(
                "limit",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "offset",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request):
        try:
            paginator = self.pagination_class()
            paginator.limit = paginator.get_limit(request)
            paginator.offset = paginator.get_offset(request)

            notifications, total = await ListFallbackNotificationsQueryHandler().handle(
                ListFallbackNotificationsQuery(
                    user_id=int(request.user.unique_id),
                    limit=paginator.limit,
                    offset=paginator.offset,
                )
            )

            paginator.count = total
            return paginator.get_paginated_response(present_notifications(notifications))
        except Exception as error:
            log_request_failed(
                logger,
                "list_fallback_notifications",
                error,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to list owned notifications: {error}",
                    "resource_id": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FallbackNotificationResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_notifications_retrieve",
        summary="Get notification details (consistent fallback)",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        try:
            notification = await GetFallbackNotificationQueryHandler().handle(
                GetFallbackNotificationQuery(
                    user_id=int(request.user.unique_id),
                    notification_id=pk,
                )
            )

            return Response(present_notification(notification), status=status.HTTP_200_OK)
        except NotificationNotFoundError as error:
            return Response(
                {
                    "message": str(error),
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as error:
            log_request_failed(
                logger,
                "get_fallback_notification",
                error,
                notification_id=pk,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to retrieve notification with ID {pk}: {error}",
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
