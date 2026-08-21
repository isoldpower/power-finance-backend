from rest_framework import serializers

from data_read_core.shared.rest_framework import MoneySerializer


class ConversionSerializer(serializers.Serializer):
    from_side = MoneySerializer()
    to = MoneySerializer()
    rate = serializers.CharField(
        help_text=(
            "The multiplier applied, as a decimal string. NOT money: no "
            "currency, no scale padding, up to 12 fraction digits. `to` is the "
            "authoritative figure — render that rather than multiplying this."
        ),
    )

    def get_fields(self):
        """`from` is a Python keyword, so the field is declared under a legal
        name and renamed before it is bound. `source` is deliberately not set —
        DRF derives it from the final name, and stating it would be redundant."""

        fields = super().get_fields()
        fields["from"] = fields.pop("from_side")

        return fields


class ConversionMetaSerializer(serializers.Serializer):
    fetched_at = serializers.DateTimeField(
        help_text="When the FEED published the rate, not when the conversion ran.",
    )


class EnvelopedConversionSerializer(serializers.Serializer):
    data = ConversionSerializer()
    meta = ConversionMetaSerializer()


class ConversionRequestSerializer(serializers.Serializer):
    """The three query params, so a missing one fails as `required` through the
    same path a missing body field would."""

    from_code = serializers.CharField()
    to_code = serializers.CharField()
    amount = serializers.CharField(
        help_text=(
            "Decimal string, validated against `from_code`'s scale. "
            "`?amount=100.005&from_code=USD` fails with 422 / `amount_precision`."
        ),
    )
