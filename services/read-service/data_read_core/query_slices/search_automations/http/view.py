from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CREATED_AT_DESC, PageRequest, build_page
from data_read_core.shared.read_at_least import es_read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import SearchAutomationsQuery
from ..query_handler import SearchAutomationsQueryHandler
from ._presenters import present_many
from ._serializers import (
    FilterAutomationsRequestSerializer,
    PaginatedAutomationSearchResultSerializer,
)


@extend_schema(
    operation_id="automations_search",
    summary="Search automations with filters",
    description=(
        "Retrieve automation rules matching a filter tree passed in the request "
        "body. POST carries the tree; this is a read in every other respect — it "
        "honours Read-At-Least and emits no write version. Served from the "
        "Elasticsearch projection. The tree filters the RULES themselves, not "
        "the resources a rule's own trigger matches."
    ),
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
    request=FilterAutomationsRequestSerializer,
    responses={
        200: PaginatedAutomationSearchResultSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["POST"])
@es_read_at_least_gate
async def search_automations(request):
    logger = get_query_logger("search_automations")
    log_request_received(
        logger,
        "search_automations",
        user_id=request.user.id,
    )

    serializer = FilterAutomationsRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    filter_body = serializer.validated_data["filter_body"]

    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filter_body,
    )
    fetched = await SearchAutomationsQueryHandler().handle(
        SearchAutomationsQuery(
            user_id=request.user.id,
            filter_body=filter_body,
            page=page_request,
        )
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "search_automations",
        user_id=request.user.id,
        total=page.total,
    )

    return ok(
        present_many(page.items),
        page.meta(cached=fetched.cached),
    )
