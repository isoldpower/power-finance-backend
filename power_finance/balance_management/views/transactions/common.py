from rest_framework import serializers

from ..wallets.get import GetWalletSerializer


class TransactionWalletPreviewSerializer(serializers.Serializer):
    wallet = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class TransactionSideDetailedSerializer(serializers.Serializer):
    wallet = GetWalletSerializer()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
