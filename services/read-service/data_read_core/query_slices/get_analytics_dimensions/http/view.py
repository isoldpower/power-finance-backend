from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import CURRENCY_PARAMETER, read_currency
from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import REPORT_NAME
from ..dtos import GetAnalyticsDimensionsQuery
from ..query_handler import GetAnalyticsDimensionsQueryHandler
from ._presenters import present_dimensions, present_meta
from ._serializers import EnvelopedDimensionsSerializer


@extend_schema(
    operation_id="analytics_dimensions_retrieve",
    summary="Get the analytics filter vocabulary",
    description=(
        "Open wallets and the distinct income and expense categories, with the "
        "first and last transaction instants. Ignores the window parameters; "
        "`currency` is only echoed back."
    ),
    parameters=[CURRENCY_PARAMETER],
    responses={
        200: EnvelopedDimensionsSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_dimensions(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    currency = await read_currency(request)
    fetched_dimensions = await GetAnalyticsDimensionsQueryHandler().handle(
        GetAnalyticsDimensionsQuery(user_id=request.user.id, currency=currency)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        present_dimensions(fetched_dimensions.resource),
        present_meta(currency, fetched_dimensions.cached),
    )
