from rest_framework import serializers


class CreateTransactionRequestSerializer(serializers.Serializer):
    source_wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class FilterTransactionsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)
