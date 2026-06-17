from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    RotateWebhookSecretCommand,
    RotateWebhookSecretCommandHandler,
)
from data_write_core.domain.exceptions import WebhookNotFoundError

from ...decorators import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    WebhookHttpPresenter,
)
from ...serializers import (
    MessageResponseSerializer,
    WebhookWithSecretResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

logger = get_http_logger("webhooks")


class WebhookSecretView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_rotate_secret",
        summary="Rotate a webhook's signing secret",
        description=(
            "Generate a fresh signing secret for the webhook. The new secret "
            "is returned only once; the previous secret stops working "
            "immediately."
        ),
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID",
            ),
        ],
        request=None,
        responses={
            200: WebhookWithSecretResponseSerializer,
            404: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, pk=None):
        try:
            handler = RotateWebhookSecretCommandHandler()
            rotated_webhook, write_version = await handler.handle(
                RotateWebhookSecretCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    webhook_id=pk,
                )
            )

            payload = WebhookHttpPresenter.present_with_secret(rotated_webhook)
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except WebhookNotFoundError as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(message=str(exc), resource_id=str(pk))
            )

            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            log_request_failed(
                logger,
                "rotate_webhook_secret",
                exc,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to rotate secret for webhook with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
