from rest_framework import serializers


class TransactionMetaResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    occurred_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    currency = serializers.CharField(allow_blank=True)
    meta = TransactionMetaResponseSerializer()


class PaginationMetaSerializer(serializers.Serializer):
    limit = serializers.IntegerField()
    offset = serializers.IntegerField()
    total = serializers.IntegerField()


class PaginatedTransactionResponseSerializer(serializers.Serializer):
    data = TransactionResponseSerializer(many=True)
    meta = PaginationMetaSerializer()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    resource_id = serializers.CharField(allow_null=True)
