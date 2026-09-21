from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response, transaction_preview_fields


class FilterTransactionsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class TransactionSearchResultSerializer(serializers.Serializer):
    pass


TransactionSearchResultSerializer._declared_fields.update(transaction_preview_fields())

PaginatedTransactionSearchResultSerializer = collection_response(TransactionSearchResultSerializer)
