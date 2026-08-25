from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CREATED_AT_DESC, PageRequest, build_page

from data_write_core.application.queries import (
    GetFallbackGoalQuery,
    GetFallbackGoalQueryHandler,
    ListFallbackGoalsQuery,
    ListFallbackGoalsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import GoalHttpPresenter
from ...serializers import (
    EnvelopedGoalResponseSerializer,
    ErrorResponseSerializer,
    PaginatedGoalResponseSerializer,
)
from ._schema import CURSOR_PARAMETER, LIMIT_PARAMETER, resource_id_parameter
from .base import FallbackReadView


class FallbackGoalListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_goals_list",
        summary="List goals (consistent fallback)",
        description=(
            "Always-consistent goal list served from the write side. The gateway "
            "routes here when the Read Service is not caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedGoalResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        page_request = PageRequest.from_request(request, CREATED_AT_DESC)
        goals, total = await ListFallbackGoalsQueryHandler().handle(
            ListFallbackGoalsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
            )
        )

        page = build_page(goals, total, page_request)
        return ok(
            await GoalHttpPresenter.present_many(page.items),
            page.meta(cached=False),
        )


class FallbackGoalResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_goals_retrieve",
        summary="Get goal details (consistent fallback)",
        description=(
            "The write side has no projected history collection, so this returns "
            "the goal without `history`. The read side is the only place that "
            "paginates it."
        ),
        parameters=[resource_id_parameter("id", "Goal ID")],
        responses={
            200: EnvelopedGoalResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, goal_id=None):
        goal = await GetFallbackGoalQueryHandler().handle(
            GetFallbackGoalQuery(
                user_id=int(request.user.unique_id),
                goal_id=goal_id,
            )
        )

        return ok(
            await GoalHttpPresenter.present_one(goal),
            {"cached": False},
        )
