from rest_framework import serializers

from .envelope import collection_response, resource_response


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField()


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Wallet ID")
    name = serializers.CharField()
    balance = MoneySerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedWalletResponseSerializer = resource_response(WalletResponseSerializer)
PaginatedWalletResponseSerializer = collection_response(WalletResponseSerializer)
