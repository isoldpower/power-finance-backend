from rest_framework import serializers


class CurrencyRatesSerializer(serializers.Serializer):
    base = serializers.CharField(
        help_text="The denominator of every rate in the map, not a converted-from code.",
    )
    rates = serializers.DictField(
        child=serializers.CharField(),
        help_text=(
            "Code to rate. Rates are decimal strings but are NOT money: they "
            "carry no currency, are unpadded, and hold up to 12 fraction digits."
        ),
    )


class CurrencyRatesMetaSerializer(serializers.Serializer):
    fetched_at = serializers.DateTimeField(
        help_text="When the FEED published these rates, not when this response was built.",
    )
    target = serializers.ListField(
        child=serializers.CharField(),
        allow_null=True,
        help_text="The `target` filter echoed back. Null when the whole map was returned.",
    )


class EnvelopedCurrencyRatesSerializer(serializers.Serializer):
    data = CurrencyRatesSerializer()
    meta = CurrencyRatesMetaSerializer()
