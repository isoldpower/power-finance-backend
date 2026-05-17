from rest_framework import serializers

from .wallet_serializer import WalletResponseSerializer


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency_code = serializers.CharField()
    source_wallet = WalletResponseSerializer()
    cancels_other = serializers.UUIDField(allow_null=True, required=False)
    adjusts_other = serializers.UUIDField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
