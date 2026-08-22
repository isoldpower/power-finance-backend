from rest_framework import serializers

from .envelope import collection_response, resource_response


class MoneySerializer(serializers.Serializer):
    amount = serializers.CharField(help_text="Decimal string at the currency's scale.")
    currency = serializers.CharField()


class WalletResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Wallet ID")
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


class WalletPeriodFlowsSerializer(serializers.Serializer):
    inflow = MoneySerializer()
    outflow = MoneySerializer(help_text="A positive magnitude, not a negative balance change.")


class WalletDetailResponseSerializer(WalletResponseSerializer):
    period = WalletPeriodFlowsSerializer(
        help_text=(
            "Money in and out over the window `?period=` asked for, resolved in "
            "the caller's timezone preference and reported in the wallet's own "
            "currency. Echoed in `meta.period`."
        )
    )


EnvelopedWalletResponseSerializer = resource_response(WalletResponseSerializer)
EnvelopedWalletDetailResponseSerializer = resource_response(WalletDetailResponseSerializer)
PaginatedWalletResponseSerializer = collection_response(WalletResponseSerializer)
