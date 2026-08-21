from rest_framework import serializers

from .envelope import collection_response, resource_response
from .wallet_serializer import WalletResponseSerializer


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField()
    wallet = WalletResponseSerializer()
    cancels_other = serializers.UUIDField(allow_null=True)
    adjusts_other = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


class TransactionPreviewResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    amount = serializers.CharField()
    currency = serializers.CharField()
    wallet_id = serializers.UUIDField()
    cancels_other = serializers.UUIDField(allow_null=True)
    adjusts_other = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedTransactionResponseSerializer = resource_response(TransactionResponseSerializer)
PaginatedTransactionResponseSerializer = collection_response(TransactionPreviewResponseSerializer)
