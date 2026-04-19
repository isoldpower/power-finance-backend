import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    BatchAcknowledgeNotificationCommand,
    BatchAcknowledgeNotificationCommandHandler,
)

from .base import NotificationView
from ...mixins import IdempotentMixin
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import MessageResponseSerializer, BatchAcknowledgeRequestSerializer

logger = logging.getLogger(__name__)


class NotificationBatchAckView(IdempotentMixin, NotificationView):
    IDEMPOTENT_ACTIONS = {'post'}
    @extend_schema(
        operation_id="notifications_batch_acknowledge",
        summary="Batch acknowledge notifications",
        description="Acknowledge receipt of multiple notifications at once.",
        request=BatchAcknowledgeRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        }
    )
    async def post(self, request):
        logger.info("NotificationBatchAckView: Received request to batch acknowledge notifications for User ID: %s", request.user.id)
        serializer = BatchAcknowledgeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            batch_ids = serializer.validated_data.get("batch", [])
            handler = BatchAcknowledgeNotificationCommandHandler()

            marked_read = await handler.handle(BatchAcknowledgeNotificationCommand(
                user_id=request.user.id,
                notification_ids=batch_ids,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Acknowledged {len(marked_read)} notification(s)",
                resource_id=None
            ))

            logger.info("NotificationBatchAckView: Successfully batch acknowledged %d notifications for User ID: %s", len(marked_read), request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to batch acknowledge notifications: {e}",
                resource_id=None
            ))

            logger.error("NotificationBatchAckView: Failed to batch acknowledge notifications for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
