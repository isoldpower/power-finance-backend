from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import (
    CREATED_AT_DESC,
    CompletePage,
    PageRequest,
    build_page,
)

from data_write_core.application.queries import (
    GetFallbackWebhookQuery,
    GetFallbackWebhookQueryHandler,
    ListFallbackWebhooksQuery,
    ListFallbackWebhooksQueryHandler,
    ListFallbackWebhookSubscriptionsQuery,
    ListFallbackWebhookSubscriptionsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    EnvelopedWebhookResponseSerializer,
    ErrorResponseSerializer,
    PaginatedWebhookResponseSerializer,
    PaginatedWebhookSubscriptionResponseSerializer,
)
from ._presenters import present_webhook, present_webhook_subscriptions, present_webhooks
from ._schema import CURSOR_PARAMETER, LIMIT_PARAMETER, resource_id_parameter
from .base import FallbackReadView

WEBHOOK_ID_PARAMETER = resource_id_parameter("id", "Webhook ID")


class FallbackWebhookListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_list",
        summary="List webhooks (consistent fallback)",
        description=(
            "Always-consistent webhook list served from the write side. The "
            "gateway routes here when the Read Service is not caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedWebhookResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        page_request = PageRequest.from_request(request, CREATED_AT_DESC)
        webhooks, total = await ListFallbackWebhooksQueryHandler().handle(
            ListFallbackWebhooksQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
            )
        )

        page = build_page(webhooks, total, page_request)
        return ok(
            present_webhooks(page.items),
            page.meta(cached=False),
        )


class FallbackWebhookResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_retrieve",
        summary="Get webhook details (consistent fallback)",
        parameters=[WEBHOOK_ID_PARAMETER],
        responses={
            200: EnvelopedWebhookResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        webhook = await GetFallbackWebhookQueryHandler().handle(
            GetFallbackWebhookQuery(
                user_id=int(request.user.unique_id),
                webhook_id=pk,
            )
        )

        return ok(
            present_webhook(webhook),
            {"cached": False},
        )


class FallbackWebhookEventListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_webhooks_subscriptions_list",
        summary="List webhook event subscriptions (consistent fallback)",
        description=(
            "Every event type the webhook is subscribed to. Bounded by the "
            "event catalogue, so this endpoint is not paginated."
        ),
        parameters=[WEBHOOK_ID_PARAMETER],
        responses={
            200: PaginatedWebhookSubscriptionResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        subscriptions = await ListFallbackWebhookSubscriptionsQueryHandler().handle(
            ListFallbackWebhookSubscriptionsQuery(
                user_id=int(request.user.unique_id),
                webhook_id=pk,
            )
        )

        page = CompletePage(subscriptions)
        return ok(
            present_webhook_subscriptions(page.items),
            page.meta(cached=False),
        )
