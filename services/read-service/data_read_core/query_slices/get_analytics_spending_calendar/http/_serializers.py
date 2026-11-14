from rest_framework import serializers

from data_read_core.shared.analytics import AnalyticsMetaSerializer, enveloped
from data_read_core.shared.rest_framework import MoneySerializer


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField(help_text="Calendar day in `timezone`.")
    inflow = MoneySerializer()
    outflow = MoneySerializer()
    net = MoneySerializer()
    transactions_count = serializers.IntegerField()


class SpendingCalendarSerializer(serializers.Serializer):
    days = CalendarDaySerializer(
        many=True,
        help_text="Every day of the window, chronological and zero-filled.",
    )
    peak_outflow = MoneySerializer(help_text="Largest single-day outflow; zero when empty.")


EnvelopedSpendingCalendarSerializer = enveloped(
    "EnvelopedAnalyticsSpendingCalendarSerializer",
    SpendingCalendarSerializer(),
    AnalyticsMetaSerializer(),
)
