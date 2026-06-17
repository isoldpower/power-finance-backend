from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.queries import (
    GetFallbackWebhookQuery,
    GetFallbackWebhookQueryHandler,
    ListFallbackWebhooksQuery,
    ListFallbackWebhooksQueryHandler,
    ListFallbackWebhookSubscriptionsQuery,
    ListFallbackWebhookSubscriptionsQueryHandler,
)
from data_write_core.domain.exceptions import WebhookNotFoundError

from ...decorators import trace_handler_flow
from ._presenters import present_webhook, present_webhook_subscriptions, present_webhooks
from .base import FallbackReadView

logger = get_http_logger("fallback_read")


class FallbackWebhookListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_list",
        summary="List webhooks (consistent fallback)",
        description=(
            "Always-consistent webhook list served from the write side. The "
            "gateway routes here when the Read Service is not caught up."
        ),
        parameters=[
            OpenApiParameter(
                "limit",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "offset",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request):
        try:
            paginator = self.pagination_class()
            paginator.limit = paginator.get_limit(request)
            paginator.offset = paginator.get_offset(request)

            webhooks, total = await ListFallbackWebhooksQueryHandler().handle(
                ListFallbackWebhooksQuery(
                    user_id=int(request.user.unique_id),
                    limit=paginator.limit,
                    offset=paginator.offset,
                )
            )

            paginator.count = total
            return paginator.get_paginated_response(present_webhooks(webhooks))
        except Exception as error:
            log_request_failed(
                logger,
                "list_fallback_webhooks",
                error,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to list owned webhooks: {error}",
                    "resource_id": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FallbackWebhookResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_retrieve",
        summary="Get webhook details (consistent fallback)",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Webhook ID",
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        try:
            webhook = await GetFallbackWebhookQueryHandler().handle(
                GetFallbackWebhookQuery(
                    user_id=int(request.user.unique_id),
                    webhook_id=pk,
                )
            )

            return Response(present_webhook(webhook), status=status.HTTP_200_OK)
        except WebhookNotFoundError as error:
            return Response(
                {
                    "message": str(error),
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as error:
            log_request_failed(
                logger,
                "get_fallback_webhook",
                error,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to retrieve webhook with ID {pk}: {error}",
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FallbackWebhookEventListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_subscriptions_list",
        summary="List webhook event subscriptions (consistent fallback)",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Webhook ID",
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        try:
            subscriptions = await ListFallbackWebhookSubscriptionsQueryHandler().handle(
                ListFallbackWebhookSubscriptionsQuery(
                    user_id=int(request.user.unique_id),
                    webhook_id=pk,
                )
            )

            return Response(
                present_webhook_subscriptions(subscriptions),
                status=status.HTTP_200_OK,
            )
        except WebhookNotFoundError as error:
            return Response(
                {
                    "message": str(error),
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as error:
            log_request_failed(
                logger,
                "list_fallback_webhook_subscriptions",
                error,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to list subscriptions of webhook {pk}: {error}",
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
