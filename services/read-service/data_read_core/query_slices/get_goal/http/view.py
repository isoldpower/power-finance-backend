from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import TRANSACTION_FEED, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import GetGoalQuery
from ..query_handler import GetGoalQueryHandler
from ._presenters import present_history_meta, present_one
from ._serializers import EnvelopedGoalDetailSerializer

HISTORY_NAMESPACE = "history"


@extend_schema(
    operation_id="goals_retrieve",
    summary="Get goal details",
    description=(
        "Retrieve a specific goal with a page of its history. `limit` and "
        "`cursor` paginate `history`, reported under `meta.history`. A closed "
        "goal still resolves by id — DELETE removes it from lists, not from "
        "existence."
    ),
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Goal ID",
        ),
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
    ],
    responses={
        200: EnvelopedGoalDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_goal(request, goal_id=None):
    logger = get_query_logger("get_goal")
    log_request_received(
        logger,
        "get_goal",
        id=goal_id,
        user_id=request.user.id,
    )

    history_request = PageRequest.from_request(request, TRANSACTION_FEED)
    fetched = await GetGoalQueryHandler().handle(
        GetGoalQuery(
            user_id=request.user.id,
            goal_id=goal_id,
            history_page=history_request,
        )
    )
    detail = fetched.resource
    history_page = build_page(
        detail.history,
        detail.history_total,
        history_request,
    )
    log_request_served(
        logger,
        "get_goal",
        id=goal_id,
    )

    return ok(
        await present_one(detail, history_page.items),
        present_history_meta(HISTORY_NAMESPACE, history_page, fetched.cached),
    )
