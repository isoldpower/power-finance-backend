from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CREATED_AT_DESC, PageRequest, build_page

from data_write_core.application.queries import (
    FallbackAutomationFilters,
    GetFallbackAutomationQuery,
    GetFallbackAutomationQueryHandler,
    ListFallbackAutomationsQuery,
    ListFallbackAutomationsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    EnvelopedAutomationResponseSerializer,
    ErrorResponseSerializer,
    PaginatedAutomationResponseSerializer,
)
from ._presenters import present_automation, present_automations
from ._query_params import resolve_tristate_flag
from ._schema import (
    CURSOR_PARAMETER,
    ENABLED_PARAMETER,
    LIMIT_PARAMETER,
    resource_id_parameter,
)
from .base import FallbackReadView

ENABLED_PARAM = "enabled"


class FallbackAutomationListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_automations_list",
        summary="List automation rules (consistent fallback)",
        description=(
            "Always-consistent automation list served from the write side. "
            "The gateway routes here when the Read Service is not caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER, ENABLED_PARAMETER],
        responses={
            200: PaginatedAutomationResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        filters = FallbackAutomationFilters(
            enabled=resolve_tristate_flag(request, ENABLED_PARAM),
        )
        page_request = PageRequest.from_request(
            request,
            CREATED_AT_DESC,
            query_material=filters.as_cursor_material(),
        )
        automations, total = await ListFallbackAutomationsQueryHandler().handle(
            ListFallbackAutomationsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
                filters=filters,
            )
        )

        page = build_page(automations, total, page_request)
        return ok(
            present_automations(page.items),
            page.meta(cached=False),
        )


class FallbackAutomationResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_automations_retrieve",
        summary="Get one automation rule (consistent fallback)",
        parameters=[resource_id_parameter("id", "Automation ID")],
        responses={
            200: EnvelopedAutomationResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, automation_id=None):
        automation = await GetFallbackAutomationQueryHandler().handle(
            GetFallbackAutomationQuery(
                user_id=int(request.user.unique_id),
                automation_id=automation_id,
            )
        )

        return ok(
            present_automation(automation),
            {"cached": False},
        )
