from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteWebhookCommand,
    DeleteWebhookCommandHandler,
    UpdateWebhookCommand,
    UpdateWebhookCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WebhookHttpPresenter
from ...serializers import (
    EnvelopedWebhookResponseSerializer,
    ErrorResponseSerializer,
    UpdateWebhookRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

WEBHOOK_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Webhook ID",
)


class WebhookResourceView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_partial_update",
        summary="Update a webhook endpoint",
        description="Update the webhook's title and/or target URL.",
        parameters=[WEBHOOK_ID_PARAMETER],
        request=UpdateWebhookRequestSerializer,
        responses={
            200: EnvelopedWebhookResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, webhook_id=None):
        serializer = UpdateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_webhook, write_version = await UpdateWebhookCommandHandler().handle(
            UpdateWebhookCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                webhook_id=webhook_id,
                title=validated.get("title"),
                url=validated.get("url"),
                enabled=validated.get("enabled"),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=WebhookHttpPresenter.present_one(
                updated_webhook,
            ),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="webhooks_delete",
        summary="Delete a webhook endpoint",
        description="Remove the webhook endpoint and all of its event subscriptions.",
        parameters=[WEBHOOK_ID_PARAMETER],
        responses={
            200: EnvelopedWebhookResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, webhook_id=None):
        deleted_webhook, write_version = await DeleteWebhookCommandHandler().handle(
            DeleteWebhookCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                webhook_id=webhook_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=WebhookHttpPresenter.present_one(
                deleted_webhook,
            ),
            write_version=write_version,
        )
