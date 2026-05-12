from rest_framework import serializers


class CategoryAnalyticsItemSerializer(serializers.Serializer):
    category = serializers.CharField(help_text="Name of the spending category")
    amount = serializers.FloatField(help_text="Total amount spent in this category")


class CategoryAnalyticsSerializer(serializers.Serializer):
    data = CategoryAnalyticsItemSerializer(many=True, help_text="List of category spending items")
    metadata = serializers.DictField(help_text="Additional analytical metadata")


class ExpenditureAnalyticsSerializer(serializers.Serializer):
    data = serializers.DictField(
        child=serializers.DictField(child=serializers.FloatField()),
        help_text="Nested dictionary containing expenditure data over time"
    )
    metadata = serializers.DictField(help_text="Additional analytical metadata")


class SpendingHeatmapSerializer(serializers.Serializer):
    data = serializers.DictField(
        child=serializers.FloatField(),
        help_text="Dictionary mapping date/time keys to spending values"
    )
    metadata = serializers.DictField(help_text="Additional analytical metadata")


class WalletBalanceHistoryItemSerializer(serializers.Serializer):
    date = serializers.DateField(help_text="The date of the balance record")
    balance = serializers.FloatField(help_text="The wallet balance on this date")


class WalletBalanceHistorySerializer(serializers.Serializer):
    data = WalletBalanceHistoryItemSerializer(many=True, help_text="List of balance records over time")
    metadata = serializers.DictField(help_text="Additional analytical metadata")


class MoneyFlowNodeSerializer(serializers.Serializer):
    name = serializers.CharField(help_text="Name of the node (e.g., wallet or category)")
    level = serializers.IntegerField(help_text="Hierarchical level of the node")


class MoneyFlowLinkSerializer(serializers.Serializer):
    source = serializers.CharField(help_text="Source node name")
    target = serializers.CharField(help_text="Target node name")
    value = serializers.FloatField(help_text="Value of the link (amount transferred)")


class MoneyFlowDataSerializer(serializers.Serializer):
    nodes = MoneyFlowNodeSerializer(many=True)
    links = MoneyFlowLinkSerializer(many=True)


class MoneyFlowAnalyticsSerializer(serializers.Serializer):
    data = MoneyFlowDataSerializer()
    metadata = serializers.DictField(help_text="Additional analytical metadata")
