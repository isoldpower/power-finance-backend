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
from ..dtos import GetAnalyticsOverviewQuery
from ..query_handler import GetAnalyticsOverviewQueryHandler
from ._presenters import present_meta, present_overview
from ._serializers import EnvelopedOverviewSerializer


@extend_schema(
    operation_id="analytics_overview_retrieve",
    summary="Get headline totals for a window and the one before it",
    description=(
        "Inflow, outflow, savings rate, activity and the largest movements for "
        "`[since, until)` and for the previous window of equal length. Transfers "
        "are excluded."
    ),
    parameters=SHARED_PARAMETERS,
    responses={
        200: EnvelopedOverviewSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_overview(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=False)
    fetched_overview = await GetAnalyticsOverviewQueryHandler().handle(
        GetAnalyticsOverviewQuery(scope=scope)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_overview(fetched_overview.resource, scope.currency),
        present_meta(scope, fetched_overview.cached),
    )
