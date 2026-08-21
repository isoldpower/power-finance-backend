from rest_framework import serializers
from write_service.common.money import MoneyAmountField


class CreateTransactionRequestSerializer(serializers.Serializer):
    source_wallet_id = serializers.UUIDField()
    amount = MoneyAmountField(
        help_text=(
            'Decimal string, e.g. "50.00". Fewer fraction digits than the '
            "currency's scale are zero-padded; more are rejected."
        ),
    )


class UpdateTransactionRequestSerializer(serializers.Serializer):
    new_amount = MoneyAmountField(
        help_text='Decimal string, e.g. "50.00".',
    )
