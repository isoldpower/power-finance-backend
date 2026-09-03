from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import ACTION_QUEUE, PageRequest, build_page

from data_write_core.application.queries import (
    FallbackActionFilters,
    ListFallbackActionsQuery,
    ListFallbackActionsQueryHandler,
)
from data_write_core.domain.entities import ActionSeverity, ActionSource, ActionStatus

from ...decorators import trace_handler_flow
from ...serializers import ErrorResponseSerializer, PaginatedActionResponseSerializer
from ._presenters import present_actions
from ._query_params import resolve_choice, resolve_choice_or
from ._schema import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    SEVERITY_PARAMETER,
    SOURCE_PARAMETER,
    STATUS_PARAMETER,
)
from .base import FallbackReadView


class FallbackActionListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_actions_list",
        summary="List the needs-action queue (consistent fallback)",
        description=(
            "Always-consistent action queue served from the write side. "
            "The gateway routes here when the Read Service is not caught up.\n\n"
            "Ordered `severity_rank DESC, created_at DESC, id DESC`, the same "
            "as the read side — a cursor minted there has to keep working here."
        ),
        parameters=[
            LIMIT_PARAMETER,
            CURSOR_PARAMETER,
            STATUS_PARAMETER,
            SOURCE_PARAMETER,
            SEVERITY_PARAMETER,
        ],
        responses={
            200: PaginatedActionResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        filters = _read_filters(request)
        page_request = PageRequest.from_request(
            request,
            ACTION_QUEUE,
            query_material=filters.as_cursor_material(),
        )
        actions, total = await ListFallbackActionsQueryHandler().handle(
            ListFallbackActionsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
                filters=filters,
            )
        )

        page = build_page(actions, total, page_request)
        return ok(
            present_actions(page.items),
            page.meta(cached=False),
        )


def _read_filters(request) -> FallbackActionFilters:
    return FallbackActionFilters(
        status=resolve_choice_or(
            request,
            "status",
            ActionStatus,
            default=ActionStatus.PENDING,
        ),
        source=resolve_choice(request, "source", ActionSource),
        severity=resolve_choice(request, "severity", ActionSeverity),
    )
