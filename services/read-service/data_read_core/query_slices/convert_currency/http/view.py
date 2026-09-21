from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import ConvertCurrencyQuery
from ..query_handler import ConvertCurrencyQueryHandler
from ._presenters import present_conversion, present_meta
from ._serializers import ConversionRequestSerializer, EnvelopedConversionSerializer


@extend_schema(
    operation_id="currencies_convert_retrieve",
    summary="Convert an amount between currencies",
    description=(
        "Converts one amount at the feed's current rate. `from` and `to` are "
        "ordinary money objects, each at its own currency's scale; `rate` is "
        "the multiplier as a plain string and carries no currency.\n\n"
        "The server rounds once, so `to` is authoritative — a client that "
        "multiplies `rate` itself can land on a different last digit.\n\n"
        "An unknown code fails with 422 `unsupported_currency`; a known code "
        "with no fresh rate fails with 409 `rate_unavailable`."
    ),
    parameters=[ConversionRequestSerializer],
    responses={
        200: EnvelopedConversionSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
async def convert_currency(request):
    logger = get_query_logger("convert_currency")
    log_request_received(logger, "convert_currency")

    serializer = ConversionRequestSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    requested = serializer.validated_data

    conversion = await ConvertCurrencyQueryHandler().handle(
        ConvertCurrencyQuery(
            from_code=requested["from_code"],
            to_code=requested["to_code"],
            raw_amount=requested["amount"],
        )
    )

    log_request_served(
        logger,
        "convert_currency",
        from_code=conversion.from_code,
        to_code=conversion.to_code,
    )

    return ok(
        present_conversion(conversion),
        present_meta(conversion),
    )
