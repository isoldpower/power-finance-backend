from rest_framework import serializers

from data_read_core.shared.analytics import FlowTotalsSerializer, Granularity, enveloped, meta_with
from data_read_core.shared.rest_framework import MoneySerializer


class AnalyticsCashFlowBucketSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    inflow = MoneySerializer()
    outflow = MoneySerializer()
    net = MoneySerializer()
    transactions_count = serializers.IntegerField()
    closing_balance = MoneySerializer(
        help_text="Signed balance of the selected wallets at `end`, transfers included.",
    )


class AnalyticsCashFlowSerializer(serializers.Serializer):
    buckets = AnalyticsCashFlowBucketSerializer(
        many=True, help_text="Chronological and zero-filled."
    )
    totals = FlowTotalsSerializer()


CashFlowMetaSerializer = meta_with(
    "AnalyticsCashFlowMetaSerializer",
    granularity=serializers.ChoiceField(choices=[granularity.value for granularity in Granularity]),
)

EnvelopedCashFlowSerializer = enveloped(
    "EnvelopedAnalyticsCashFlowSerializer",
    AnalyticsCashFlowSerializer(),
    CashFlowMetaSerializer(),
)
