from rest_framework.request import Request

from data_read_core.shared.money import CURRENCY_CATALOG, parse_amount

from ..dtos import ALL_GROUPS, ChartFilters
from ._serializers import ChartRequestSerializer

LOWBAR_FIELD = "lowbar"


async def read_filters(request: Request) -> ChartFilters:
    serializer = ChartRequestSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    requested = serializer.validated_data

    currency = await CURRENCY_CATALOG.require(requested["currency"])
    raw_lowbar = requested["lowbar"]

    return ChartFilters(
        group=requested.get("group") or ALL_GROUPS,
        lowbar=parse_amount(raw_lowbar, currency.digits, LOWBAR_FIELD),
        currency=currency.code,
    )
