from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteNotificationCommand,
    DeleteNotificationCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import NotificationHttpPresenter
from ...serializers import (
    EnvelopedNotificationResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import NotificationView


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
            200: EnvelopedNotificationResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        deleted_notification, write_version = await DeleteNotificationCommandHandler().handle(
            DeleteNotificationCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                notification_id=pk,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=NotificationHttpPresenter.present_one(
                deleted_notification,
            ),
            write_version=write_version,
        )
