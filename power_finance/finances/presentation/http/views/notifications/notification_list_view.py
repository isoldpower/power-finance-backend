import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    ListNotificationsQuery,
    ListNotificationsQueryHandler,
)

from .base import NotificationView
from ...presenters import CommonHttpPresenter, MessageResultInfo, NotificationHttpPresenter
from ...serializers import MessageResponseSerializer, NotificationResponseSerializer

logger = logging.getLogger(__name__)


class NotificationListView(NotificationView):
    @extend_schema(
        operation_id="notifications_list",
        summary="List notifications",
        description="Retrieve a paginated list of your notifications.",
        responses={
            200: NotificationResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    async def get(self, request):
        logger.info("NotificationListView: Received request to list notifications for User ID: %s", request.user.id)
        try:
            handler = ListNotificationsQueryHandler()
            notifications = await handler.handle(ListNotificationsQuery(
                user_id=request.user.id
            ))

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(notifications, request)
            payload = NotificationHttpPresenter.present_many(queryset_page)

            logger.info("NotificationListView: Successfully listed %d notifications for User ID: %s", len(queryset_page) if queryset_page else 0, request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list notifications: {e}",
                resource_id=None
            ))

            logger.error("NotificationListView: Failed to list notifications for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
