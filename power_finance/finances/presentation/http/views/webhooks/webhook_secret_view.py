import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    RotateWebhookSecretCommandHandler, RotateWebhookSecretCommand,
)

from .base import WebhookView
from ...mixins import IdempotentMixin
from ...presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ...serializers import (
    MessageResponseSerializer,
    RotateWebhookSecretRequestSerializer,
    WebhookWithSecretResponseSerializer,
)

logger = logging.getLogger(__name__)


class WebhookSecretView(IdempotentMixin, WebhookView):
    IDEMPOTENT_ACTIONS = {'post'}
    @extend_schema(
        operation_id="webhooks_rotate_secret",
        summary="Rotate webhook secret",
        description="Rotate the signing secret for this webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=RotateWebhookSecretRequestSerializer,
        responses={
            200: WebhookWithSecretResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def post(self, request: Request, pk: str | None = None) -> Response:
        logger.info(
            "WebhookSecretView: Received request to rotate secret for Webhook ID: %s for User ID: %s",
            pk, request.user.id
        )
        serializer = RotateWebhookSecretRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            handler = RotateWebhookSecretCommandHandler()
            rotated_webhook = await handler.handle(RotateWebhookSecretCommand(
                webhook_id=pk,
                user_id=request.user.id,
            ))
            payload = WebhookHttpPresenter.present_one_with_secret(rotated_webhook)

            logger.info(
                "WebhookSecretView: Successfully rotated secret for Webhook ID: %s for User ID: %s",
                pk, request.user.id
            )
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to rotate the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error(
                "WebhookSecretView: Failed to rotate secret for Webhook ID: %s for User ID: %s - %s",
                pk, request.user.id, str(e)
            )
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
