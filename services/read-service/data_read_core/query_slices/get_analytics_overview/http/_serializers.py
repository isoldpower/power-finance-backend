from rest_framework import serializers

from data_read_core.shared.analytics import (
    AnalyticsMetaSerializer,
    TransactionBriefSerializer,
    enveloped,
)
from data_read_core.shared.rest_framework import MoneySerializer


class TopCategorySerializer(serializers.Serializer):
    category = serializers.CharField(allow_null=True)
    amount = MoneySerializer()
    share = serializers.FloatField(help_text="Percentage of the window's outflow.")


class PeriodSummarySerializer(serializers.Serializer):
    since = serializers.DateTimeField()
    until = serializers.DateTimeField()
    inflow = MoneySerializer()
    outflow = MoneySerializer()
    net = MoneySerializer(help_text="Signed: `inflow - outflow`.")
    savings_rate = serializers.FloatField(
        allow_null=True,
        help_text="`net / inflow * 100`. Null when nothing came in.",
    )
    transactions_count = serializers.IntegerField(
        help_text="Income and expense rows, no transfers."
    )
    active_days = serializers.IntegerField(help_text="Days in `timezone` with at least one row.")
    average_daily_outflow = MoneySerializer()
    largest_expense = TransactionBriefSerializer(allow_null=True)
    largest_income = TransactionBriefSerializer(allow_null=True)
    top_expense_category = TopCategorySerializer(allow_null=True)


class OverviewSerializer(serializers.Serializer):
    current = PeriodSummarySerializer()
    previous = PeriodSummarySerializer(help_text="The window of equal length just before.")


EnvelopedOverviewSerializer = enveloped(
    "EnvelopedAnalyticsOverviewSerializer",
    OverviewSerializer(),
    AnalyticsMetaSerializer(),
)
