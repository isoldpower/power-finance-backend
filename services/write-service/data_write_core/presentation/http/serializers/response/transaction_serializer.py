from rest_framework import serializers

from .envelope import collection_response, resource_response
from .wallet_serializer import MoneySerializer


class TransactionWalletSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    money = MoneySerializer(help_text="A positive magnitude; direction is `type`.")
    type = serializers.CharField(help_text="expense or income, derived from the money's sign.")
    origin = serializers.CharField()
    wallet = TransactionWalletSerializer()
    category = serializers.CharField(allow_null=True)
    chain_id = serializers.UUIDField(allow_null=True)


class TransactionChainResponseSerializer(serializers.Serializer):
    chain_id = serializers.UUIDField()
    transactions = TransactionResponseSerializer(many=True)


class TransactionFlowSerializer(serializers.Serializer):
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
EnvelopedTransactionChainResponseSerializer = resource_response(TransactionChainResponseSerializer)
PaginatedTransactionResponseSerializer = collection_response(TransactionResponseSerializer)
PaginatedTransactionFlowSerializer = collection_response(TransactionFlowSerializer)
