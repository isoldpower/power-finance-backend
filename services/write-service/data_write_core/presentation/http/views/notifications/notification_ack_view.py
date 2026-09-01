from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    AcknowledgeNotificationsCommand,
    AcknowledgeNotificationsCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import NotificationHttpPresenter
from ...serializers import (
    EnvelopedNotificationResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import NotificationView


class NotificationAckView(NotificationView, CommandResponseMixin):
    @extend_schema(
        operation_id="notifications_acknowledge",
        summary="Acknowledge a notification",
        description=(
            "Mark a notification as read and return it.\n\n"
            "Idempotent by nature, so it needs no `Idempotency-Key`: "
            "acknowledging an already-read notification succeeds and returns it "
            "unchanged, keeping the original `acknowledged_at`. It is not a 409 "
            "- the caller's intent is already satisfied. There is no "
            "un-acknowledge."
        ),
        parameters=[
            OpenApiParameter(
                "notification_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Notification ID",
            ),
        ],
        request=None,
        responses={
            200: EnvelopedNotificationResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, notification_id=None):
        acknowledged, write_version = await AcknowledgeNotificationsCommandHandler().handle(
            AcknowledgeNotificationsCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                notification_ids=(notification_id,),
                strict=True,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=NotificationHttpPresenter.present_one(acknowledged[0]),
            write_version=write_version,
        )
