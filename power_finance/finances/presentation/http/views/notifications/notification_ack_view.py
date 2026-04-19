import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    AcknowledgeNotificationCommand,
    AcknowledgeNotificationCommandHandler,
)

from .base import NotificationView
from ...mixins import IdempotentMixin
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import MessageResponseSerializer

logger = logging.getLogger(__name__)


class NotificationAckView(IdempotentMixin, NotificationView):
    IDEMPOTENT_ACTIONS = {'post'}
    @extend_schema(
        operation_id="notifications_acknowledge",
        summary="Acknowledge notification",
        description="Acknowledge receipt of a notification, marking it as delivered. This stops the SSE stream from sending it again.",
        parameters=[
            OpenApiParameter(
                'notification_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Notification ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
            403: MessageResponseSerializer,
            404: MessageResponseSerializer,
        }
    )
    async def post(self, request, notification_id=None):
        logger.info("NotificationAckView: Received request to acknowledge Notification ID: %s for User ID: %s", notification_id, request.user.id)
        try:
            handler = AcknowledgeNotificationCommandHandler()
            notification = await handler.handle(AcknowledgeNotificationCommand(
                user_id=request.user.id,
                notification_id=notification_id,
            ))

            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Acknowledged notification with ID {notification.id}",
                resource_id=f"{notification.id}"
            ))

            logger.info("NotificationAckView: Successfully acknowledged Notification ID: %s for User ID: %s", notification_id, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except PermissionError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))

            logger.error("NotificationAckView: Permission denied acknowledging Notification ID: %s for User ID: %s - %s", notification_id, request.user.id, str(e))
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))

            logger.error("NotificationAckView: Notification ID: %s not found for User ID: %s - %s", notification_id, request.user.id, str(e))
            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("NotificationAckView: Failed to acknowledge Notification ID: %s for User ID: %s - %s", notification_id, request.user.id, str(e))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to acknowledge notification: {e}",
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
