from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CREATED_AT_DESC, PageRequest, build_page

from data_write_core.application.queries import (
    CountFallbackNotificationsQuery,
    CountFallbackNotificationsQueryHandler,
    GetFallbackNotificationQuery,
    GetFallbackNotificationQueryHandler,
    ListFallbackNotificationsQuery,
    ListFallbackNotificationsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    EnvelopedNotificationCountsResponseSerializer,
    EnvelopedNotificationResponseSerializer,
    ErrorResponseSerializer,
    PaginatedNotificationResponseSerializer,
)
from ._presenters import (
    present_notification,
    present_notification_counts,
    present_notifications,
)
from ._schema import CURSOR_PARAMETER, LIMIT_PARAMETER, resource_id_parameter
from .base import FallbackReadView


class FallbackNotificationListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_notifications_list",
        summary="List notifications (consistent fallback)",
        description=(
            "Always-consistent notification list served from the write side. "
            "The gateway routes here when the Read Service is not caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedNotificationResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        page_request = PageRequest.from_request(request, CREATED_AT_DESC)
        notifications, total = await ListFallbackNotificationsQueryHandler().handle(
            ListFallbackNotificationsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
            )
        )

        page = build_page(notifications, total, page_request)
        return ok(
            present_notifications(page.items),
            page.meta(cached=False),
        )


class FallbackNotificationResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_notifications_retrieve",
        summary="Get notification details (consistent fallback)",
        parameters=[resource_id_parameter("id", "Notification ID")],
        responses={
            200: EnvelopedNotificationResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, notification_id=None):
        notification = await GetFallbackNotificationQueryHandler().handle(
            GetFallbackNotificationQuery(
                user_id=int(request.user.unique_id),
                notification_id=notification_id,
            )
        )

        return ok(
            present_notification(notification),
            {"cached": False},
        )


class FallbackNotificationCountView(FallbackReadView):
    """The bell badge. It is routed BEFORE the resource view, which would
    otherwise not match `count` at all — the resource path takes a UUID — but
    the ordering is what keeps that true if the resource path ever loosens."""

    @extend_schema(
        operation_id="fallback_notifications_count",
        summary="Count unacknowledged notifications (consistent fallback)",
        description=(
            "Always-consistent badge counts served from the write side. "
            "The gateway routes here when the Read Service is not caught up."
        ),
        responses={
            200: EnvelopedNotificationCountsResponseSerializer,
            401: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        counts = await CountFallbackNotificationsQueryHandler().handle(
            CountFallbackNotificationsQuery(user_id=int(request.user.unique_id))
        )

        return ok(present_notification_counts(counts), {})
