from rest_framework import serializers

from data_read_core.shared.rest_framework import MoneySerializer, collection_response


class FilterWalletsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class WalletSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    category = serializers.CharField(allow_blank=True)
    currency = serializers.CharField()
    money = MoneySerializer(help_text="The spendable balance, not what the user owns.")
    zero_balance = MoneySerializer()
    favorite = serializers.BooleanField()
    color = serializers.CharField(allow_blank=True)


PaginatedWalletSearchResultSerializer = collection_response(WalletSearchResultSerializer)
