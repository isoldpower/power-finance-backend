from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    build_page,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import ListAccountsQuery
from ..query_handler import ListAccountsQueryHandler
from ._filters import read_filters
from ._presenters import present_many, present_meta
from ._serializers import ChartRequestSerializer, PaginatedAccountPreviewSerializer


@extend_schema(
    operation_id="accounts_list",
    summary="List ledger accounts",
    description=(
        "Retrieve a page of your double-entry chart of accounts, newest first. "
        "These accounts are derived by the backend from your transactions; they "
        "are not created or edited directly.\n\n"
        "`group` narrows the page but never reorders it — assets do not lead "
        "liabilities. `meta.groups` reports every group regardless, so the tab "
        "labels do not change when a tab is selected."
    ),
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER, ChartRequestSerializer],
    responses={
        200: PaginatedAccountPreviewSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_accounts(request):
    logger = get_query_logger("list_accounts")
    log_request_received(
        logger,
        "list_accounts",
        user_id=request.user.id,
    )

    filters = await read_filters(request)
    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filters.as_cache_material(),
    )
    fetched_accounts = await ListAccountsQueryHandler().handle(
        ListAccountsQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters,
        )
    )

    response_page = build_page(
        fetched_accounts.rows,
        fetched_accounts.total,
        page_request,
    )
    log_request_served(
        logger,
        "list_accounts",
        user_id=request.user.id,
        total=response_page.total,
    )

    return ok(
        await present_many(response_page.items),
        await present_meta(
            response_page,
            filters,
            fetched_accounts.groups,
            fetched_accounts.cached,
        ),
    )
