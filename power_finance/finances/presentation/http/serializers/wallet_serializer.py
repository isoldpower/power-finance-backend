from rest_framework import serializers
from .money_field_serializer import MoneyField


class CreateWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    credit = serializers.BooleanField()
    balance = MoneyField()


class UpdateWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    credit = serializers.BooleanField(required=False)
    balance = MoneyField(required=False)


class ReplaceWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    credit = serializers.BooleanField()
    balance = MoneyField()