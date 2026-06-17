from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    CreateWebhookCommand,
    CreateWebhookCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    WebhookHttpPresenter,
)
from ...serializers import (
    CreateWebhookRequestSerializer,
    MessageResponseSerializer,
    WebhookWithSecretResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

logger = get_http_logger("webhooks")


class WebhookListView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_create",
        summary="Create a webhook endpoint",
        description=(
            "Register an outbound webhook endpoint. The signing secret is "
            "returned only once — store it on receipt."
        ),
        request=CreateWebhookRequestSerializer,
        responses={
            201: WebhookWithSecretResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = CreateWebhookCommandHandler()
            created_webhook, write_version = await handler.handle(
                CreateWebhookCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    title=validated["title"],
                    url=validated["url"],
                )
            )

            payload = WebhookHttpPresenter.present_with_secret(created_webhook)
            return self.form_write_response(
                response_body=payload,
                status_code=status.HTTP_201_CREATED,
                write_version=write_version,
            )
        except Exception as exc:
            log_request_failed(
                logger,
                "create_webhook",
                exc,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to create webhook: {exc}",
                    resource_id=None,
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
