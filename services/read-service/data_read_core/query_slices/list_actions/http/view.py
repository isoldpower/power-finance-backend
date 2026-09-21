from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import ACTION_QUEUE, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..config import (
    SEVERITY_PARAMETER,
    SOURCE_PARAMETER,
    STATUS_PARAMETER,
)
from ..dtos import ListActionsQuery
from ..query_handler import ListActionsQueryHandler
from ._filters import read_filters
from ._presenters import present_many
from ._serializers import PaginatedActionPreviewSerializer


@extend_schema(
    operation_id="actions_list",
    summary="List the needs-action queue",
    description=(
        "Things you must DECIDE about, most urgent first.\n\n"
        "Ordered `severity DESC, created_at DESC, id DESC`. Unlike the "
        "notification feed this IS a queue to be worked through, so a critical "
        "action outranks an older informational one.\n\n"
    ),
    parameters=[
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
        STATUS_PARAMETER,
        SOURCE_PARAMETER,
        SEVERITY_PARAMETER,
    ],
    responses={
        200: PaginatedActionPreviewSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_actions(request):
    logger = get_query_logger("list_actions")
    log_request_received(logger, "list_actions", user_id=request.user.id)

    filters = read_filters(request)
    page_request = PageRequest.from_request(
        request,
        ACTION_QUEUE,
        query_material=filters.as_cache_material(),
    )
    fetched = await ListActionsQueryHandler().handle(
        ListActionsQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters,
        )
    )

    actions_page = build_page(
        fetched.rows,
        fetched.total,
        page_request,
    )
    log_request_served(
        logger,
        "list_actions",
        user_id=request.user.id,
        total=actions_page.total,
    )

    return ok(
        present_many(actions_page.items),
        actions_page.meta(cached=fetched.cached),
    )
