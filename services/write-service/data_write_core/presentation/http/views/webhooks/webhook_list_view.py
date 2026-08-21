from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateWebhookCommand,
    CreateWebhookCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WebhookHttpPresenter
from ...serializers import (
    CreateWebhookRequestSerializer,
    EnvelopedWebhookWithSecretResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView


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
            201: EnvelopedWebhookWithSecretResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        created_webhook, write_version = await CreateWebhookCommandHandler().handle(
            CreateWebhookCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                title=validated["title"],
                url=validated["url"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=WebhookHttpPresenter.present_with_secret(
                created_webhook,
            ),
            write_version=write_version,
        )
