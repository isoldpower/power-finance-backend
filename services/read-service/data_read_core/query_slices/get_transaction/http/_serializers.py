from rest_framework import serializers

from data_read_core.shared.rest_framework import resource_response


class TransactionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    wallet_id = serializers.UUIDField()
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField(allow_blank=True)
    occurred_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedTransactionDetailSerializer = resource_response(TransactionDetailSerializer)
