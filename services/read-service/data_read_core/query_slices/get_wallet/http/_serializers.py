from rest_framework import serializers

from data_read_core.shared.rest_framework import MoneySerializer, resource_response


class WalletDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    balance = MoneySerializer()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedWalletDetailSerializer = resource_response(WalletDetailSerializer)
