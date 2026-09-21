from rest_framework.request import Request

from data_read_core.shared.money import CURRENCY_CATALOG, parse_amount

from ..config import GroupFilter, ParamsList
from ..dtos import ChartFilters
from ._serializers import ChartRequestSerializer


async def read_filters(request: Request) -> ChartFilters:
    serializer = ChartRequestSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    requested = serializer.validated_data

    currency = await CURRENCY_CATALOG.require(requested["currency"])
    raw_lowbar = requested["lowbar"]

    return ChartFilters(
        group=requested.get("group") or GroupFilter.ALL,
        lowbar=parse_amount(raw_lowbar, currency.digits, ParamsList.LOWBAR),
        currency=currency.code,
    )
