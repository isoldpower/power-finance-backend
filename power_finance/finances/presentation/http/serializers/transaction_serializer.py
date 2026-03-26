from rest_framework import serializers
from .wallet_serializer import WalletResponseSerializer


class TransactionParticipantField(serializers.Serializer):
    wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class CreateTransactionRequestSerializer(serializers.Serializer):
    sender = TransactionParticipantField(required=False)
    receiver = TransactionParticipantField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.CharField()
    category = serializers.CharField(required=False)


class UpdateTransactionRequestSerializer(serializers.Serializer):
    description = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    type = serializers.CharField(required=False)


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
