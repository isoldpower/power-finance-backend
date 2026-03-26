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


class WalletBalanceResponseSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, help_text="Current balance amount")
    currency = serializers.CharField(help_text="Currency code")


class WalletMetaResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Wallet ID")
    created_at = serializers.DateTimeField(help_text="Creation timestamp")
    updated_at = serializers.DateTimeField(help_text="Last update timestamp")


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Unique identifier of the wallet")
    name = serializers.CharField(help_text="Name of the wallet")
    credit = serializers.BooleanField(help_text="Credit status of the wallet")
    balance = WalletBalanceResponseSerializer(help_text="Current balance details")
    meta = WalletMetaResponseSerializer(help_text="Wallet metadata")