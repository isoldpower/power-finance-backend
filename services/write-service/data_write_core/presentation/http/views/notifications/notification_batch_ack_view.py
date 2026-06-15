from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    AcknowledgeNotificationsCommand,
    AcknowledgeNotificationsCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import (
    BatchAcknowledgeRequestSerializer,
    MessageResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import NotificationView

logger = get_http_logger("notifications")


class NotificationBatchAckView(NotificationView, CommandResponseMixin):
    @extend_schema(
        operation_id="notifications_batch_acknowledge",
        summary="Acknowledge notifications in batch",
        description=(
            "Mark several notifications as read at once. Unknown or "
            "already-read ids are skipped silently."
        ),
        request=BatchAcknowledgeRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = BatchAcknowledgeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            batch_ids = serializer.validated_data["batch"]
            handler = AcknowledgeNotificationsCommandHandler()
            acknowledged_ids, write_version = await handler.handle(
                AcknowledgeNotificationsCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    notification_ids=tuple(batch_ids),
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Acknowledged {len(acknowledged_ids)} notification(s)",
                    resource_id=None,
                )
            )
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            log_request_failed(
                logger,
                "batch_acknowledge_notifications",
                exc,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to batch acknowledge notifications: {exc}",
                    resource_id=None,
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
