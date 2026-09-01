from rest_framework import serializers

from data_read_core.shared.money import DEFAULT_CURRENCY
from data_read_core.shared.rest_framework import (
    CollectionMetaSerializer,
    MoneySerializer,
)

from ..dtos import ALL_GROUPS, GROUP_CHOICES


class AccountPreviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group = serializers.CharField(
        allow_blank=True,
        help_text="assets, liabilities or equity; blank when ungrouped",
    )
    name = serializers.CharField()
    money = MoneySerializer(
        help_text=(
            "The account's balance in the BOOK currency it is summed in, not "
            "in the currency of the transactions behind it."
        ),
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


class ChartMetaSerializer(CollectionMetaSerializer):
    lowbar = serializers.CharField(
        help_text="The threshold actually applied, at `currency`'s scale.",
    )
    currency = serializers.CharField(help_text="The currency `lowbar` was read in.")
    group = serializers.CharField(help_text="The group filter actually applied.")
    groups = serializers.DictField(
        child=serializers.IntegerField(),
        help_text=(
            "Per-group counts for the tab labels. NOT narrowed by `group` — it "
            "always describes every group — but `lowbar` does apply, so a "
            "count matches what selecting that tab returns."
        ),
    )


class PaginatedAccountPreviewSerializer(serializers.Serializer):
    data = AccountPreviewSerializer(many=True)
    meta = ChartMetaSerializer()


class ChartRequestSerializer(serializers.Serializer):
    group = serializers.ChoiceField(
        choices=GROUP_CHOICES,
        required=False,
        default=ALL_GROUPS,
        help_text="Narrow the chart to one group. `all` is the default.",
    )
    lowbar = serializers.CharField(
        required=False,
        default="0",
        help_text=(
            "Hide accounts whose balance is smaller than this in MAGNITUDE, so "
            "a threshold does not silently drop every liability. Money Shape "
            "grammar, validated against `currency`'s scale."
        ),
    )
    currency = serializers.CharField(
        required=False,
        default=DEFAULT_CURRENCY,
        help_text="The currency `lowbar` is expressed in. Unknown codes 422.",
    )
