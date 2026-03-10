from rest_framework import serializers
from decimal import Decimal

from finances.models import Currency, Money


class MoneyField(serializers.Serializer):
    """
    Handles nested { "amount": "123.45", "currency": "USD" } in ISO 4217 codes
    """

    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal('0.00'),
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
        internal_data = super().to_internal_value(data)
        amount = internal_data.get('amount')
        code = internal_data.get('currency')

        try:
            currency_instance = Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            raise serializers.ValidationError({
                "currency": f"Currency '{code}' does not exist."
            })

        return Money(amount=amount, currency=currency_instance)

    def to_representation(self, value):
        if value is None:
            return None

        return {
            "amount": value.amount.quantize(Decimal('0.01')),
            "currency": value.currency.code
        }
