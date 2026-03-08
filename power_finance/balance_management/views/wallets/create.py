from rest_framework import serializers

from .common import MetaSerializer
from ..money import MoneyField
from ...models import Wallet


class CreateWalletSerializer(MetaSerializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    credit = serializers.BooleanField()
    balance = MoneyField()

    class Meta:
        model = Wallet
        fields = ['id', 'name', 'balance', 'credit', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        return Wallet.objects.create(**validated_data)

