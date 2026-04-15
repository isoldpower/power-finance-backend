import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    DeleteWebhookCommand,
    DeleteWebhookCommandHandler,
    UpdateWebhookEndpointCommandHandler,
    UpdateWebhookEndpointCommand,
    GetWebhookQueryHandler,
    GetWebhookQuery,
)

from .base import WebhookView
from ...presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ...serializers import (
    UpdateWebhookRequestSerializer,
    WebhookResponseSerializer,
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class WebhookResourceView(WebhookView):
    @extend_schema(
        operation_id="webhooks_retrieve",
        summary="Get webhook details",
        description="Retrieve detailed information about a specific webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: WebhookResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request, pk: str) -> Response:
        try:
            logger.info("WebhookResourceView: Received request to retrieve Webhook ID: %s for User ID: %s", pk, request.user.id)
            handler = GetWebhookQueryHandler()
            requested_hook = await handler.handle(GetWebhookQuery(
                user_id=request.user.id,
                webhook_id=pk,
            ))
            payload = WebhookHttpPresenter.present_one(requested_hook)

            logger.info("WebhookResourceView: Successfully retrieved Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to retrieve the Webhook Endpoint:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhookResourceView: Failed to retrieve Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_delete",
        summary="Delete a webhook",
        description="Delete a specific webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def delete(self, request: Request, pk: str | None = None) -> Response:
        logger.info("WebhookResourceView: Received request to delete Webhook ID: %s for User ID: %s", pk, request.user.id)
        try:
            handler = DeleteWebhookCommandHandler()
            deleted_hook = await handler.handle(DeleteWebhookCommand(
                user_id=request.user.id,
                webhook_id=pk,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Successfully deleted Webhook with ID {deleted_hook.id}",
                resource_id=f"{pk}"
            ))

            logger.info("WebhookResourceView: Successfully deleted Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WebhookResourceView: Failed to delete Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_partial_update",
        summary="Update a webhook",
        description="Update the title or URL of an existing webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=UpdateWebhookRequestSerializer,
        responses={
            200: WebhookResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def patch(self, request: Request, pk: str | None = None) -> Response:
        logger.info("WebhookResourceView: Received request to update Webhook ID: %s for User ID: %s", pk, request.user.id)
        serializer = UpdateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = UpdateWebhookEndpointCommandHandler()
            result = await handler.handle(UpdateWebhookEndpointCommand(
                webhook_id=pk,
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
            ))
            payload = WebhookHttpPresenter.present_one(result)

            logger.info("WebhookResourceView: Successfully updated Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WebhookResourceView: Failed to update Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
