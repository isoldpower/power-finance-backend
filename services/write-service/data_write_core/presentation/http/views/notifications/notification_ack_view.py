from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    AcknowledgeNotificationsCommand,
    AcknowledgeNotificationsCommandHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    AcknowledgedNotificationsResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import NotificationView


class NotificationAckView(NotificationView, CommandResponseMixin):
    @extend_schema(
        operation_id="notifications_acknowledge",
        summary="Acknowledge a notification",
        description=(
            "Mark a notification as read. Acknowledging an already-read " "notification is a no-op."
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
            200: AcknowledgedNotificationsResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, notification_id=None):
        acknowledged_ids, write_version = await AcknowledgeNotificationsCommandHandler().handle(
            AcknowledgeNotificationsCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                notification_ids=(notification_id,),
                strict=True,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body={"acknowledged_ids": [str(item) for item in acknowledged_ids]},
            write_version=write_version,
        )
