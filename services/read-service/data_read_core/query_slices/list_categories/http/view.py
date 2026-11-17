from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CATEGORY_LISTING, PageRequest, build_page
from data_read_core.shared.postgres_orm import CategoryKinds
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..config import ParamsList
from ..dtos import ListCategoriesQuery
from ..query_handler import ListCategoriesQueryHandler
from ._presenters import present_many
from ._query_params import resolve_kind
from ._serializers import PaginatedCategorySerializer

KIND_PARAMETER = OpenApiParameter(
    ParamsList.KIND,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[kind.value for kind in CategoryKinds],
    description="Restrict to transaction or wallet categories. Absent means both.",
)


@extend_schema(
    operation_id="categories_list",
    summary="List categories",
    description=(
        "The categories you can assign: the global ones every user sees, then "
        "your own, each group alphabetical. Deleted categories are left out, "
        "though wallets and transactions that already use one still show it."
    ),
    parameters=[KIND_PARAMETER, LIMIT_PARAMETER, CURSOR_PARAMETER],
    responses={
        200: PaginatedCategorySerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_categories(request):
    logger = get_query_logger("list_categories")
    log_request_received(logger, "list_categories", user_id=request.user.id)

    kind = resolve_kind(request)
    page_request = PageRequest.from_request(request, CATEGORY_LISTING)
    fetched = await ListCategoriesQueryHandler().handle(
        ListCategoriesQuery(user_id=request.user.id, page=page_request, kind=kind)
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(logger, "list_categories", user_id=request.user.id, total=page.total)

    return ok(present_many(page.items), page.meta(cached=fetched.cached))
