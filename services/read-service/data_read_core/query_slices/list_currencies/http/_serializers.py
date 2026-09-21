from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class CurrencySerializer(serializers.Serializer):
    code = serializers.CharField(help_text="ISO-4217 alphabetic code.")
    symbol = serializers.CharField(
        help_text="Display symbol. Empty when the currency has no established one.",
    )
    name = serializers.CharField()
    decimals = serializers.IntegerField(
        help_text="Fraction digits every amount in this currency is rendered at.",
    )


CurrencyCollectionResponseSerializer = collection_response(
    CurrencySerializer,
    component_name="CurrencyCollectionSerializer",
)
