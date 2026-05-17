from rest_framework import serializers


class CreateWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)


class UpdateWalletRequestSerializer(serializers.Serializer):
    """Request body for renaming a wallet. Balance/currency are derived
    from the immutable transaction history and cannot be patched."""

    new_name = serializers.CharField(max_length=120)
