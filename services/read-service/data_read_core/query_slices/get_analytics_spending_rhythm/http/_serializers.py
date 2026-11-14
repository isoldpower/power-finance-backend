from rest_framework import serializers

from data_read_core.shared.analytics import AnalyticsMetaSerializer, enveloped
from data_read_core.shared.rest_framework import MoneySerializer


class RhythmCellSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(help_text="ISO weekday: 1 is Monday, 7 is Sunday.")
    hour = serializers.IntegerField(help_text="0..23 in `timezone`.")
    amount = MoneySerializer()
    transactions_count = serializers.IntegerField()


class RhythmPeakSerializer(serializers.Serializer):
    weekday = serializers.IntegerField()
    hour = serializers.IntegerField()
    amount = MoneySerializer()


class SpendingRhythmSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="`expense` or `income`.")
    cells = RhythmCellSerializer(
        many=True,
        help_text="All 168 cells, ordered by weekday then hour.",
    )
    peak = RhythmPeakSerializer(allow_null=True, help_text="Null when every cell is zero.")


EnvelopedSpendingRhythmSerializer = enveloped(
    "EnvelopedAnalyticsSpendingRhythmSerializer",
    SpendingRhythmSerializer(),
    AnalyticsMetaSerializer(),
)
