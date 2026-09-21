from rest_framework import serializers

from data_read_core.shared.rest_framework import (
    MoneySerializer,
    resource_response,
    transaction_preview_fields,
)


class WalletPeriodFlowsSerializer(serializers.Serializer):
    inflow = MoneySerializer()
    outflow = MoneySerializer(help_text="A positive magnitude, not a negative balance change.")


class WalletRecentTransactionSerializer(serializers.Serializer):
    pass


WalletRecentTransactionSerializer._declared_fields.update(transaction_preview_fields())


class WalletDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    category = serializers.CharField(allow_blank=True)
    currency = serializers.CharField()
    money = MoneySerializer(help_text="The spendable balance, not what the user owns.")
    zero_balance = MoneySerializer()
    favorite = serializers.BooleanField()
    color = serializers.CharField(allow_blank=True)
    recent = WalletRecentTransactionSerializer(
        many=True,
        help_text=(
            "The wallet's own transaction feed, paginated through this "
            "endpoint's limit/cursor and reported in `meta.recent`."
        ),
    )
    period = WalletPeriodFlowsSerializer(
        help_text=(
            "Money in and out over the window `?period=` asked for, resolved in "
            "the caller's timezone preference and reported in the wallet's own "
            "currency. Echoed in `meta.period`."
        )
    )


EnvelopedWalletDetailSerializer = resource_response(WalletDetailSerializer)
