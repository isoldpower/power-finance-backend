from rest_framework import serializers

from data_read_core.shared.analytics import collection_meta_with, enveloped
from data_read_core.shared.rest_framework import CategoryReferenceSerializer, MoneySerializer


class CounterpartySerializer(serializers.Serializer):
    name = serializers.CharField(help_text="The most frequent original spelling.")
    category = CategoryReferenceSerializer(
        allow_null=True,
        help_text="The counterparty's most frequent category.",
    )
    amount = MoneySerializer()
    share = serializers.FloatField(help_text="Percentage of the side's total in the window.")
    transactions_count = serializers.IntegerField()
    average = MoneySerializer()
    last_seen_at = serializers.DateTimeField()


CounterpartiesMetaSerializer = collection_meta_with(
    "AnalyticsCounterpartiesMetaSerializer",
    total_counterparties=serializers.IntegerField(
        help_text="Distinct counterparties before `limit`.",
    ),
)

EnvelopedCounterpartiesSerializer = enveloped(
    "EnvelopedAnalyticsCounterpartiesSerializer",
    CounterpartySerializer(many=True),
    CounterpartiesMetaSerializer(),
)
