from rest_framework import serializers


class WalletBalanceSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Wallet ID")
    name = serializers.CharField()
    user_id = serializers.IntegerField()
    balance = WalletBalanceSerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
