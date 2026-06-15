from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    DeleteNotificationCommand,
    DeleteNotificationCommandHandler,
)
from data_write_core.domain.exceptions import NotificationNotFoundError

from ...decorators import trace_handler_flow
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import MessageResponseSerializer
from ..mixins import CommandResponseMixin
from .base import NotificationView

logger = get_http_logger("notifications")


class NotificationResourceView(NotificationView, CommandResponseMixin):
    @extend_schema(
        operation_id="notifications_delete",
        summary="Delete a notification",
        description="Permanently remove a notification from the user's inbox.",
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
        responses={
            200: MessageResponseSerializer,
            404: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        try:
            handler = DeleteNotificationCommandHandler()
            deleted_notification, write_version = await handler.handle(
                DeleteNotificationCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    notification_id=pk,
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Deleted notification with ID {deleted_notification.id}",
                    resource_id=str(deleted_notification.id),
                )
            )
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except NotificationNotFoundError as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=str(exc),
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            log_request_failed(
                logger,
                "delete_notification",
                exc,
                notification_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to delete notification with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
