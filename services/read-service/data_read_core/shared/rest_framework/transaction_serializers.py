from rest_framework import serializers

from .money_serializers import MoneySerializer


class TransactionWalletSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)


class TransactionChainSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    size = serializers.IntegerField(
        help_text="How many live transactions the chain currently carries."
    )


def transaction_preview_fields() -> dict:
    return {
        "id": serializers.UUIDField(),
        "name": serializers.CharField(allow_blank=True),
        "created_at": serializers.DateTimeField(),
        "updated_at": serializers.DateTimeField(allow_null=True),
        "deleted_at": serializers.DateTimeField(allow_null=True),
        "money": MoneySerializer(help_text="A positive magnitude; direction is `type`."),
        "type": serializers.CharField(
            help_text="expense or income, read off the sign of the folded ledger flows."
        ),
        "origin": serializers.CharField(),
        "wallet": TransactionWalletSerializer(),
        "category": serializers.CharField(allow_null=True),
        "chain": TransactionChainSerializer(allow_null=True),
    }
