from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    CATEGORY_PARAMETER,
    SHARED_PARAMETERS,
    read_analytics_scope,
    read_side,
    side_parameter,
)
from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import REPORT_NAME
from ..dtos import GetAnalyticsCategoriesQuery
from ..query_handler import GetAnalyticsCategoriesQueryHandler
from ._presenters import present_categories, present_meta
from ._serializers import EnvelopedCategoriesSerializer


@extend_schema(
    operation_id="analytics_categories_retrieve",
    summary="Break one side of the ledger down by category",
    description=(
        "Every category with rows in the window, amount descending, each compared "
        "with the same category in the previous window. Transfers are excluded."
    ),
    parameters=[*SHARED_PARAMETERS, side_parameter(required_default=True), CATEGORY_PARAMETER],
    responses={
        200: EnvelopedCategoriesSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_categories(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=True)
    fetched_categories = await GetAnalyticsCategoriesQueryHandler().handle(
        GetAnalyticsCategoriesQuery(scope=scope, side=read_side(request))
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_categories(fetched_categories.resource, scope.currency),
        present_meta(scope, fetched_categories.cached),
    )
