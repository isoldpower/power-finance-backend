from rest_framework import serializers

from data_read_core.shared.analytics import WalletOptionSerializer, enveloped, meta_with
from data_read_core.shared.rest_framework import MoneySerializer


class WalletBalanceSeriesSerializer(serializers.Serializer):
    wallet = WalletOptionSerializer()
    balances = MoneySerializer(many=True, help_text="Signed, in the requested currency.")
    native_balances = MoneySerializer(many=True, help_text="Signed, in the wallet's currency.")


class BalanceHistorySerializer(serializers.Serializer):
    timestamps = serializers.ListField(
        child=serializers.DateTimeField(),
        help_text="`points` evenly spaced instants; the first is `since`, the last `until`.",
    )
    total = MoneySerializer(many=True, help_text="Sum of the converted wallet balances.")
    wallets = WalletBalanceSeriesSerializer(many=True, help_text="Same order as `/dimensions`.")


BalanceHistoryMetaSerializer = meta_with(
    "AnalyticsBalanceHistoryMetaSerializer",
    points=serializers.IntegerField(),
)

EnvelopedBalanceHistorySerializer = enveloped(
    "EnvelopedAnalyticsBalanceHistorySerializer",
    BalanceHistorySerializer(),
    BalanceHistoryMetaSerializer(),
)
