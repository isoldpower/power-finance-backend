from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    CATEGORY_PARAMETER,
    GRANULARITY_PARAMETER,
    SHARED_PARAMETERS,
    build_buckets,
    read_analytics_scope,
    read_granularity,
    resolve_granularity,
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
from ..dtos import GetAnalyticsCashFlowQuery
from ..query_handler import GetAnalyticsCashFlowQueryHandler
from ._presenters import present_cash_flow, present_meta
from ._serializers import EnvelopedCashFlowSerializer


@extend_schema(
    operation_id="analytics_cash_flow_retrieve",
    summary="Get inflow and outflow per time bucket",
    description=(
        "Zero-filled buckets aligned to calendar boundaries in `timezone`, each with "
        "inflow, outflow, net and the closing balance of the selected wallets."
    ),
    parameters=[*SHARED_PARAMETERS, GRANULARITY_PARAMETER, CATEGORY_PARAMETER],
    responses={
        200: EnvelopedCashFlowSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_cash_flow(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=True)
    granularity = resolve_granularity(read_granularity(request), scope.window)
    fetched_cash_flow = await GetAnalyticsCashFlowQueryHandler().handle(
        GetAnalyticsCashFlowQuery(
            scope=scope,
            granularity=granularity,
            buckets=build_buckets(scope.window, granularity, scope.zone),
        )
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_cash_flow(fetched_cash_flow.resource, scope.currency),
        present_meta(scope, granularity, fetched_cash_flow.cached),
    )
