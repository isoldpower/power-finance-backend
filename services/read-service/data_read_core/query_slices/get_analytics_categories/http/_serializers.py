from rest_framework import serializers

from data_read_core.shared.analytics import AnalyticsMetaSerializer, enveloped
from data_read_core.shared.rest_framework import MoneySerializer


class CategoryShareSerializer(serializers.Serializer):
    category = serializers.CharField(allow_null=True, help_text="Null for uncategorised rows.")
    amount = MoneySerializer()
    share = serializers.FloatField(help_text="Percentage of `total`.")
    transactions_count = serializers.IntegerField()
    average = MoneySerializer(help_text="`amount / transactions_count`.")
    previous_amount = MoneySerializer(help_text="Same category in the previous window.")
    change_percentage = serializers.FloatField(
        allow_null=True,
        help_text="Null when the previous amount was zero.",
    )


class CategoriesSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="`expense` or `income`.")
    total = MoneySerializer()
    categories = CategoryShareSerializer(
        many=True,
        help_text="Every category with rows in the window, amount descending.",
    )


EnvelopedCategoriesSerializer = enveloped(
    "EnvelopedAnalyticsCategoriesSerializer",
    CategoriesSerializer(),
    AnalyticsMetaSerializer(),
)
