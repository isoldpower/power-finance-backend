from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    DeleteWebhookCommand,
    DeleteWebhookCommandHandler,
    UpdateWebhookCommand,
    UpdateWebhookCommandHandler,
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
    UpdateWebhookRequestSerializer,
    WebhookResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

logger = get_http_logger("webhooks")

_WEBHOOK_ID_PARAMETER = OpenApiParameter(
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
        parameters=[_WEBHOOK_ID_PARAMETER],
        request=UpdateWebhookRequestSerializer,
        responses={
            200: WebhookResponseSerializer,
            404: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, pk=None):
        serializer = UpdateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = UpdateWebhookCommandHandler()
            updated_webhook, write_version = await handler.handle(
                UpdateWebhookCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    webhook_id=pk,
                    title=validated.get("title"),
                    url=validated.get("url"),
                )
            )

            payload = WebhookHttpPresenter.present_one(updated_webhook)
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
                "update_webhook",
                exc,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to update webhook with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id="webhooks_delete",
        summary="Delete a webhook endpoint",
        description="Remove the webhook endpoint and all of its event subscriptions.",
        parameters=[_WEBHOOK_ID_PARAMETER],
        responses={
            200: MessageResponseSerializer,
            404: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        try:
            handler = DeleteWebhookCommandHandler()
            deleted_webhook, write_version = await handler.handle(
                DeleteWebhookCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    webhook_id=pk,
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Deleted webhook with ID {deleted_webhook.id}",
                    resource_id=str(deleted_webhook.id),
                )
            )
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
                "delete_webhook",
                exc,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to delete webhook with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
