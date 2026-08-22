from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response, transaction_preview_fields


class TransactionPreviewSerializer(serializers.Serializer):
    """The target's transaction preview."""


TransactionPreviewSerializer._declared_fields.update(transaction_preview_fields())

PaginatedTransactionPreviewSerializer = collection_response(TransactionPreviewSerializer)
