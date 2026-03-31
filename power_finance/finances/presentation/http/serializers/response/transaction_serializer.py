from rest_framework import serializers
from .wallet_serializer import WalletResponseSerializer


class TransactionParticipantPreviewSerializer(serializers.Serializer):
    wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class TransactionParticipantDetailedSerializer(serializers.Serializer):
    wallet = WalletResponseSerializer()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class TransactionMetaSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    created_at = serializers.DateTimeField(help_text="Creation timestamp")


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    type = serializers.CharField(help_text="Transaction type")
    sender = TransactionParticipantDetailedSerializer(allow_null=True)
    receiver = TransactionParticipantDetailedSerializer(allow_null=True)
    description = serializers.CharField(allow_blank=True)
    meta = TransactionMetaSerializer()


class TransactionPreviewResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Transaction ID")
    type = serializers.CharField(help_text="Transaction type")
    sender = TransactionParticipantPreviewSerializer(allow_null=True)
    receiver = TransactionParticipantPreviewSerializer(allow_null=True)
    description = serializers.CharField(allow_blank=True)
    meta = TransactionMetaSerializer()
