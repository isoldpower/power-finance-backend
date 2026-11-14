from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    CATEGORY_PARAMETER,
    GRANULARITY_PARAMETER,
    SHARED_PARAMETERS,
    bounded_integer_parameter,
    build_buckets,
    read_analytics_scope,
    read_bounded_integer,
    read_granularity,
    read_side,
    resolve_granularity,
    side_parameter,
)
from data_read_core.shared.http_contract import DetailCode, ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import LIMIT_BOUNDS, REPORT_NAME
from ..dtos import GetAnalyticsCategoryTrendsQuery
from ..query_handler import GetAnalyticsCategoryTrendsQueryHandler
from ._presenters import present_category_trends, present_meta
from ._serializers import EnvelopedCategoryTrendsSerializer


@extend_schema(
    operation_id="analytics_category_trends_retrieve",
    summary="Get per-category series over time",
    description=(
        "One zero-filled series per featured category, aligned to the `/cash-flow` "
        "buckets. Without a `category` filter the top `limit` categories are kept and "
        "the rest fold into one `__other__` series; with one, exactly those "
        "categories come back and no roll-up."
    ),
    parameters=[
        *SHARED_PARAMETERS,
        side_parameter(required_default=True),
        GRANULARITY_PARAMETER,
        bounded_integer_parameter(LIMIT_BOUNDS, "How many categories to feature."),
        CATEGORY_PARAMETER,
    ],
    responses={
        200: EnvelopedCategoryTrendsSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_category_trends(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=True)
    granularity = resolve_granularity(read_granularity(request), scope.window)
    buckets = build_buckets(scope.window, granularity, scope.zone)
    fetched_trends = await GetAnalyticsCategoryTrendsQueryHandler().handle(
        GetAnalyticsCategoryTrendsQuery(
            scope=scope,
            side=read_side(request),
            granularity=granularity,
            buckets=buckets,
            limit=read_bounded_integer(request, LIMIT_BOUNDS, DetailCode.LIMIT_OUT_OF_RANGE),
        )
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_category_trends(fetched_trends.resource, buckets, scope.currency),
        present_meta(scope, granularity, fetched_trends.cached),
    )
