from rest_framework import serializers

from data_read_core.shared.analytics import WalletOptionSerializer, enveloped


class CategoryCatalogSerializer(serializers.Serializer):
    expense = serializers.ListField(child=serializers.CharField(), help_text="A to Z.")
    income = serializers.ListField(child=serializers.CharField(), help_text="A to Z.")


class DimensionsSerializer(serializers.Serializer):
    wallets = WalletOptionSerializer(
        many=True,
        help_text="Open wallets, favourites first, then by name.",
    )
    categories = CategoryCatalogSerializer()
    first_transaction_at = serializers.DateTimeField(
        allow_null=True,
        help_text="Null when the ledger is empty.",
    )
    last_transaction_at = serializers.DateTimeField(allow_null=True)


class DimensionsMetaSerializer(serializers.Serializer):
    currency = serializers.CharField(help_text="Echoed back.")
    generated_at = serializers.DateTimeField()
    cached = serializers.BooleanField(required=False)


EnvelopedDimensionsSerializer = enveloped(
    "EnvelopedAnalyticsDimensionsSerializer",
    DimensionsSerializer(),
    DimensionsMetaSerializer(),
)
