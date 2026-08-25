from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CREATED_AT_DESC, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import ListGoalsQuery
from ..query_handler import ListGoalsQueryHandler
from ._presenters import present_many, present_meta
from ._serializers import PaginatedGoalPreviewSerializer


@extend_schema(
    operation_id="goals_list",
    summary="List goals",
    description=(
        "Retrieve a page of your savings goals, newest first. Goals do not sort "
        "by `finish_at` or by completion — a goal does not move in the list "
        "because its deadline approaches. Closed goals are excluded."
    ),
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
    responses={
        200: PaginatedGoalPreviewSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_goals(request):
    logger = get_query_logger("list_goals")
    log_request_received(
        logger,
        "list_goals",
        user_id=request.user.id,
    )

    page_request = PageRequest.from_request(request, CREATED_AT_DESC)
    fetched = await ListGoalsQueryHandler().handle(
        ListGoalsQuery(user_id=request.user.id, page=page_request)
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_goals",
        user_id=request.user.id,
        total=page.total,
    )

    return ok(
        await present_many(page.items),
        present_meta(page, fetched.cached),
    )
