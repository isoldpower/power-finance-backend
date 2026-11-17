from rest_framework import serializers

from data_read_core.shared.analytics import Granularity, enveloped, meta_with
from data_read_core.shared.rest_framework import CategoryReferenceSerializer, MoneySerializer

from ..config import SeriesKind


class BucketBoundsSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class CategorySeriesSerializer(serializers.Serializer):
    key = serializers.CharField(help_text="Category id, `__none__` or `__other__`.")
    category = CategoryReferenceSerializer(
        allow_null=True,
        help_text="Null for uncategorised rows and for the other roll-up.",
    )
    kind = serializers.ChoiceField(choices=[kind.value for kind in SeriesKind])
    total = MoneySerializer()
    points = MoneySerializer(many=True, help_text="Exactly one per bucket, in bucket order.")


class CategoryTrendsSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="`expense` or `income`.")
    buckets = BucketBoundsSerializer(many=True, help_text="Identical to `/cash-flow` buckets.")
    series = CategorySeriesSerializer(
        many=True,
        help_text="Top `limit` categories by total, then one `other` series if anything remains.",
    )


CategoryTrendsMetaSerializer = meta_with(
    "AnalyticsCategoryTrendsMetaSerializer",
    granularity=serializers.ChoiceField(choices=[granularity.value for granularity in Granularity]),
)

EnvelopedCategoryTrendsSerializer = enveloped(
    "EnvelopedAnalyticsCategoryTrendsSerializer",
    CategoryTrendsSerializer(),
    CategoryTrendsMetaSerializer(),
)
