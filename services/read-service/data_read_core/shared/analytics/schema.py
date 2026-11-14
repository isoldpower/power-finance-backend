from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

from data_read_core.shared.rest_framework import CollectionMetaSerializer, MoneySerializer

from .config import Granularity, IntegerBounds, LedgerSide, ParamsList


def _query_parameter(name: str, parameter_type, description: str, **options) -> OpenApiParameter:
    return OpenApiParameter(
        name,
        type=parameter_type,
        location=OpenApiParameter.QUERY,
        description=description,
        **options,
    )


SINCE_PARAMETER = _query_parameter(
    ParamsList.SINCE,
    OpenApiTypes.DATETIME,
    "Inclusive start of the window. Defaults to `until` minus 30 days.",
)
UNTIL_PARAMETER = _query_parameter(
    ParamsList.UNTIL,
    OpenApiTypes.DATETIME,
    "Exclusive end of the window. Defaults to now. At most 5 years after `since`.",
)
CURRENCY_PARAMETER = _query_parameter(
    ParamsList.CURRENCY,
    OpenApiTypes.STR,
    "ISO-4217 target currency for every amount. Defaults to the user's main currency.",
)
WALLET_PARAMETER = _query_parameter(
    ParamsList.WALLET_ID,
    OpenApiTypes.STR,
    "Comma-joined wallet ids. Defaults to every open wallet.",
)
TIMEZONE_PARAMETER = _query_parameter(
    ParamsList.TIMEZONE,
    OpenApiTypes.STR,
    "IANA zone that cuts days, ISO weeks, months and hours of day. Defaults to UTC.",
)
CATEGORY_PARAMETER = _query_parameter(
    ParamsList.CATEGORY,
    OpenApiTypes.STR,
    "Comma-joined category names. `__none__` selects uncategorised rows.",
)
GRANULARITY_PARAMETER = _query_parameter(
    ParamsList.GRANULARITY,
    OpenApiTypes.STR,
    "Bucket width. Chosen from the window length when omitted.",
    enum=[granularity.value for granularity in Granularity],
)


def side_parameter(*, required_default: bool) -> OpenApiParameter:
    return _query_parameter(
        ParamsList.TYPE,
        OpenApiTypes.STR,
        "Ledger side. Defaults to `expense`."
        if required_default
        else "Ledger side. Both when omitted.",
        enum=[side.value for side in LedgerSide],
    )


def bounded_integer_parameter(bounds: IntegerBounds, description: str) -> OpenApiParameter:
    return _query_parameter(
        bounds.parameter,
        OpenApiTypes.INT,
        f"{description} {bounds.minimum}..{bounds.maximum}, default {bounds.default}.",
    )


SHARED_PARAMETERS = [
    SINCE_PARAMETER,
    UNTIL_PARAMETER,
    CURRENCY_PARAMETER,
    WALLET_PARAMETER,
    TIMEZONE_PARAMETER,
]


class AnalyticsMetaSerializer(serializers.Serializer):
    since = serializers.DateTimeField(help_text="Effective window start after defaults.")
    until = serializers.DateTimeField(help_text="Effective window end after defaults.")
    currency = serializers.CharField()
    timezone = serializers.CharField()
    wallet_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_null=True,
        help_text="Null means every wallet.",
    )
    categories = serializers.ListField(
        child=serializers.CharField(),
        allow_null=True,
        help_text="Null means no category filter.",
    )
    generated_at = serializers.DateTimeField()
    cached = serializers.BooleanField(required=False)


class WalletReferenceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    color = serializers.CharField()


class WalletOptionSerializer(WalletReferenceSerializer):
    currency = serializers.CharField(help_text="The wallet's own currency.")


class TransactionBriefSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    created_at = serializers.DateTimeField()
    type = serializers.CharField(help_text="`expense` or `income`.")
    category = serializers.CharField(allow_null=True)
    wallet = WalletReferenceSerializer()
    money = MoneySerializer(help_text="Native amount, in the wallet's currency.")
    converted = MoneySerializer(help_text="The same amount in the requested currency.")


class FlowTotalsSerializer(serializers.Serializer):
    inflow = MoneySerializer()
    outflow = MoneySerializer()
    net = MoneySerializer()


def enveloped(component_name: str, data_field: serializers.Field, meta_field: serializers.Field):
    return type(
        component_name,
        (serializers.Serializer,),
        {"data": data_field, "meta": meta_field},
    )


def meta_with(component_name: str, **extra_fields: serializers.Field):
    return type(component_name, (AnalyticsMetaSerializer,), extra_fields)


def collection_meta_with(component_name: str, **extra_fields: serializers.Field):
    return type(component_name, (AnalyticsMetaSerializer, CollectionMetaSerializer), extra_fields)
