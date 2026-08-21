from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class FilterTransactionsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class TransactionSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    wallet_id = serializers.UUIDField()
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField()
    occurred_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


PaginatedTransactionSearchResultSerializer = collection_response(TransactionSearchResultSerializer)
