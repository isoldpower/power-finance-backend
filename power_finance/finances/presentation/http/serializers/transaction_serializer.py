from rest_framework import serializers


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
