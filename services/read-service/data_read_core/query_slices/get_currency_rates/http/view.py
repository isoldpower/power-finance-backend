from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import GetCurrencyRatesQuery
from ..query_handler import GetCurrencyRatesQueryHandler
from ._presenters import present_meta, present_rates
from ._query_params import TARGET_PARAMETER, read_target_codes
from ._serializers import EnvelopedCurrencyRatesSerializer


@extend_schema(
    operation_id="currencies_rates_retrieve",
    summary="Get exchange rates against a base currency",
    description=(
        "Every rate the feed carries, expressed against the currency in the "
        "path. Nothing is converted here, so the field is `base` — the "
        "denominator of the map — rather than `from`.\n\n"
        "A code this API does not know fails with 422 `unsupported_currency`. A "
        "known code the feed has no fresh reading for fails with 409 "
        "`rate_unavailable` rather than returning an old number."
    ),
    parameters=[
        OpenApiParameter(
            "code",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="ISO-4217 code the rates are expressed against.",
        ),
        OpenApiParameter(
            TARGET_PARAMETER,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            many=True,
            description=(
                "Restrict the map to these codes. Repeat the param or pass a "
                "comma-separated list. Absent returns every rate the feed has."
            ),
        ),
    ],
    responses={
        200: EnvelopedCurrencyRatesSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
async def get_currency_rates(request, code=None):
    logger = get_query_logger("get_currency_rates")
    log_request_received(logger, "get_currency_rates", base=code)

    rates = await GetCurrencyRatesQueryHandler().handle(
        GetCurrencyRatesQuery(
            base_code=code,
            target_codes=read_target_codes(request),
        )
    )

    log_request_served(
        logger,
        "get_currency_rates",
        base=rates.base,
    )

    return ok(
        present_rates(rates),
        present_meta(rates),
    )
