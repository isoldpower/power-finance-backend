from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import SHARED_PARAMETERS, read_analytics_scope
from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import REPORT_NAME
from ..dtos import GetAnalyticsMoneyFlowQuery
from ..query_handler import GetAnalyticsMoneyFlowQueryHandler
from ._presenters import present_meta, present_money_flow
from ._serializers import EnvelopedMoneyFlowSerializer


@extend_schema(
    operation_id="analytics_money_flow_retrieve",
    summary="Get the income to wallet to expense flow",
    description=(
        "A three-column acyclic flow for a Sankey chart. A wallet's surplus flows to "
        "`savings`; a shortfall is drawn from `reserves`. Transfers are excluded."
    ),
    parameters=SHARED_PARAMETERS,
    responses={
        200: EnvelopedMoneyFlowSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_money_flow(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=False)
    fetched_money_flow = await GetAnalyticsMoneyFlowQueryHandler().handle(
        GetAnalyticsMoneyFlowQuery(scope=scope)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_money_flow(fetched_money_flow.resource, scope.currency),
        present_meta(scope, fetched_money_flow.cached),
    )
