from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    AcknowledgeNotificationsCommand,
    AcknowledgeNotificationsCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import NotificationHttpPresenter
from ...serializers import (
    BatchAcknowledgeRequestSerializer,
    ErrorResponseSerializer,
    PaginatedNotificationResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import NotificationView


class NotificationBatchAckView(NotificationView, CommandResponseMixin):
    @extend_schema(
        operation_id="notifications_batch_acknowledge",
        summary="Acknowledge notifications in batch",
        description=(
            "Mark several notifications as read at once. Not in the target "
            "document; kept because a bell with twenty unread items needs it.\n\n"
            "Unknown ids are skipped silently rather than failing the batch, "
            "and an already-read one keeps its original `acknowledged_at`. The "
            "response carries every notification named in the request, in the "
            "same shape as `GET /notifications`."
        ),
        request=BatchAcknowledgeRequestSerializer,
        responses={
            200: PaginatedNotificationResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = BatchAcknowledgeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        acknowledged, write_version = await AcknowledgeNotificationsCommandHandler().handle(
            AcknowledgeNotificationsCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                notification_ids=tuple(serializer.validated_data["batch"]),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=NotificationHttpPresenter.present_many(acknowledged),
            write_version=write_version,
        )
