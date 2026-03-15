from rest_framework import serializers
from decimal import Decimal


class MoneyField(serializers.Serializer):
    """
    Handles nested { "amount": "123.45", "currency": "USD" } in ISO 4217 codes
    """

    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=True,
        error_messages={'required': 'Initial balance amount is required.'}
    )

    currency = serializers.CharField(
        max_length=3,
        required=True,
        trim_whitespace=True,
        error_messages={'required': 'Currency code is required.'}
    )

    def to_internal_value(self, data):
        internal = super().to_internal_value(data)

        return {
            "amount": internal["amount"],
            "currency": internal["currency"].upper(),
        }

    def to_representation(self, value):
        if value is None:
            return None

        return {
            "amount": value.amount.quantize(Decimal("0.01")),
            "currency": value.currency,
        }
