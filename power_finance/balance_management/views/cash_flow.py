from decimal import Decimal

from rest_framework import serializers

from power_finance.balance_management.models import Currency, Wallet, Money


class CashFlowField(serializers.Serializer):
    """
    Handles nested { "wallet": "..." "amount": xxxx } as a balance adjustment
    """

    wallet = serializers.UUIDField(
        required=True,
        error_messages={'required': 'Wallet ID is required for balance adjustment.'}
    )
    amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=True,
        error_messages={'required': 'Balance adjustment must have an amount.'}
    )

    def to_internal_value(self, data):
        internal_data = super().to_internal_value(data)
        amount = internal_data.get('amount')
        code = internal_data.get('currency')
        wallet_id = internal_data.get('wallet')

        try:
            currency_instance = Currency.objects.get(code=code.upper())
        except Currency.DoesNotExist:
            raise serializers.ValidationError({
                "currency": f"Currency '{code}' does not exist."
            })

        try:
            wallet_instance = Wallet.objects.get(wallet_id=wallet_id)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({
                "wallet": f"Wallet '{wallet_id}' does not exist."
            })

        return {
            "wallet": wallet_instance.wallet,
            "money": Money(amount=amount, currency=currency_instance.code),
        }

    def to_representation(self, value):
        if value is None:
            return None

        return {
            "wallet": str(value.wallet.id),
            "amount": value.amount.quantize(Decimal('0.01')),
            "currency": value.currency.code
        }