from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class AccountPreviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group = serializers.CharField(
        allow_blank=True,
        help_text="assets, liabilities or equity; blank when ungrouped",
    )
    name = serializers.CharField()
    balance = serializers.CharField(help_text="Ledger total as a decimal string")
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


PaginatedAccountPreviewSerializer = collection_response(AccountPreviewSerializer)
