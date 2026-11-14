from rest_framework import serializers

from data_read_core.shared.analytics import (
    AnalyticsMetaSerializer,
    WalletReferenceSerializer,
    enveloped,
)
from data_read_core.shared.rest_framework import MoneySerializer

from ..config import FlowNodeKind


class FlowNodeSerializer(serializers.Serializer):
    id = serializers.CharField(
        help_text=(
            "`income:<category|__none__>`, `wallet:<id>`, `expense:<category|__none__>`, "
            "`savings` or `reserves`."
        ),
    )
    kind = serializers.ChoiceField(choices=[kind.value for kind in FlowNodeKind])
    label = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    wallet = WalletReferenceSerializer(allow_null=True, help_text="Set only for wallet nodes.")
    amount = MoneySerializer(help_text="The larger of the node's total in and total out.")


class FlowLinkSerializer(serializers.Serializer):
    source = serializers.CharField()
    target = serializers.CharField()
    amount = MoneySerializer()


class MoneyFlowTotalsSerializer(serializers.Serializer):
    inflow = MoneySerializer()
    outflow = MoneySerializer()


class MoneyFlowSerializer(serializers.Serializer):
    nodes = FlowNodeSerializer(many=True)
    links = FlowLinkSerializer(
        many=True,
        help_text="Each `(source, target)` pair appears at most once, amount descending.",
    )
    totals = MoneyFlowTotalsSerializer()


EnvelopedMoneyFlowSerializer = enveloped(
    "EnvelopedAnalyticsMoneyFlowSerializer",
    MoneyFlowSerializer(),
    AnalyticsMetaSerializer(),
)
