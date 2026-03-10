from rest_framework import serializers

from ..money import MoneyField
from finances.models import Wallet


class ListWalletsSerializer(serializers.ModelSerializer):
    balance = MoneyField(read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'name', 'balance', 'credit']
        read_only_fields = fields
