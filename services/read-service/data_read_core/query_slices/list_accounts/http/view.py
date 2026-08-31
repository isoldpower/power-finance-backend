from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import (
    ACCOUNT_CHART,
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
from ._presenters import present_many
from ._serializers import PaginatedAccountPreviewSerializer


@extend_schema(
    operation_id="accounts_list",
    summary="List ledger accounts",
    description=(
        "Retrieve a page of your double-entry chart of accounts, ordered by "
        "group then name. These accounts are derived by the backend from your "
        "transactions; they are not created or edited directly."
    ),
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
    responses={
        200: PaginatedAccountPreviewSerializer,
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

    page_request = PageRequest.from_request(request, ACCOUNT_CHART)
    fetched = await ListAccountsQueryHandler().handle(
        ListAccountsQuery(user_id=request.user.id, page=page_request)
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_accounts",
        user_id=request.user.id,
        total=page.total,
    )

    return ok(
        await present_many(page.items),
        page.meta(cached=fetched.cached),
    )
