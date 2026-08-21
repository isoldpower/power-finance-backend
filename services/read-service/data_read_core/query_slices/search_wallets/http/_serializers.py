from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class FilterWalletsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField()


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    balance = MoneySerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


PaginatedWalletResponseSerializer = collection_response(WalletResponseSerializer)
