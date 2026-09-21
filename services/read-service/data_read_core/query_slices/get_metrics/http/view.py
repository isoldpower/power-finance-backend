from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.metrics import read_points, read_since
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import GetMetricsQuery
from ..query_handler import GetMetricsQueryHandler
from ._presenters import present_meta, present_metrics
from ._selection import read_sections
from ._serializers import EnvelopedMetricsSerializer, MetricsRequestSerializer


@extend_schema(
    operation_id="metrics_retrieve",
    summary="Get the balance sheet, net worth and cash flow",
    description=(
        "All three derived views in one response.\n\n"
        "`balance`, `net-worth` and `cash-flow` are booleans that each default "
        "to TRUE - a bare request returns everything. Send `?cash-flow=false` "
        "to drop a section; it comes back as `null` rather than disappearing, "
        "so the three keys are always present."
    ),
    parameters=[MetricsRequestSerializer],
    responses={
        200: EnvelopedMetricsSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_metrics(request):
    logger = get_query_logger("get_metrics")
    log_request_received(
        logger,
        "get_metrics",
        user_id=request.user.id,
    )

    window = read_since(request)
    chart_points = read_points(request)
    sections = read_sections(request)
    fetched_metrics = await GetMetricsQueryHandler().handle(
        GetMetricsQuery(
            user_id=request.user.id,
            currency=request.user.preferences.currency,
            window=window,
            points=chart_points,
            sections=sections,
        )
    )
    log_request_served(
        logger,
        "get_metrics",
        user_id=request.user.id,
    )

    return ok(
        await present_metrics(fetched_metrics.resource),
        present_meta(
            window,
            chart_points,
            sections,
            fetched_metrics.cached,
        ),
    )
