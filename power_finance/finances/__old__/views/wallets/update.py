from rest_framework import serializers

from .common import MetaSerializer
from ..money import MoneyField
from finances.models import Wallet


class UpdateWalletSerializer(MetaSerializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    credit = serializers.BooleanField()
    balance = MoneyField()

    class Meta:
        model = Wallet
        fields = ['id', 'name', 'balance', 'credit', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance
