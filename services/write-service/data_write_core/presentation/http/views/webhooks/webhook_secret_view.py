from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    RotateWebhookSecretCommand,
    RotateWebhookSecretCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WebhookHttpPresenter
from ...serializers import (
    EnvelopedWebhookWithSecretResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

WEBHOOK_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Webhook ID",
)


class WebhookSecretView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_rotate_secret",
        summary="Rotate a webhook's signing secret",
        description=(
            "Generate a fresh signing secret for the webhook. The new secret "
            "is returned only once; the previous secret stops working "
            "immediately."
        ),
        parameters=[WEBHOOK_ID_PARAMETER],
        request=None,
        responses={
            200: EnvelopedWebhookWithSecretResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, pk=None):
        rotated_webhook, write_version = await RotateWebhookSecretCommandHandler().handle(
            RotateWebhookSecretCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                webhook_id=pk,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=WebhookHttpPresenter.present_with_secret(
                rotated_webhook,
            ),
            write_version=write_version,
        )
