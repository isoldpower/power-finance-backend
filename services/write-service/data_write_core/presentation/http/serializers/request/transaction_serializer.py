from rest_framework import serializers


class CreateTransactionRequestSerializer(serializers.Serializer):
    source_wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)


class UpdateTransactionRequestSerializer(serializers.Serializer):
    """Request body for adjusting an existing transaction's amount.
    Update semantics changed from the monolith: the original transaction
    stays untouched and a new adjustment transaction is appended."""

    new_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
