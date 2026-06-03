from rest_framework import serializers


class WalletBalanceResponseSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    currency = serializers.CharField()


class WalletMetaResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    balance = WalletBalanceResponseSerializer()
    meta = WalletMetaResponseSerializer()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    resource_id = serializers.CharField()
