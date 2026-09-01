from rest_framework import serializers

from data_read_core.shared.metrics import PointsCount
from data_read_core.shared.rest_framework import MoneySerializer

from ..dtos import ALL_SECTIONS, Direction


class BalanceSheetSerializer(serializers.Serializer):
    assets = MoneySerializer()
    liabilities = MoneySerializer()
    equity = MoneySerializer()
    balanced = serializers.BooleanField(
        help_text=(
            "True when `assets == liabilities + equity` AND no transaction was "
            "posted with legs that disagreed. A diagnostic, never an error."
        ),
    )
    comments = serializers.CharField(
        allow_null=True,
        help_text="Why the sheet does not balance. Null when it does.",
    )


class SeriesPointSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(
        help_text="The END of the slice this point summarises.",
    )
    money = MoneySerializer(
        help_text="Net worth as it stood at that moment.",
    )


class NetDiffSerializer(serializers.Serializer):
    percentage = serializers.FloatField(
        allow_null=True,
        help_text=(
            "Growth over the window as a bare number — not money, so no "
            "currency and no scale. Null when the window opened at zero, where "
            "any change is infinite growth."
        ),
    )
    direction = serializers.ChoiceField(
        choices=[direction.value for direction in Direction],
        help_text="`flat` is a real value, not the absence of a direction.",
    )


class NetWorthSerializer(serializers.Serializer):
    money = MoneySerializer(
        help_text="Net worth NOW, not at the end of the window.",
    )
    net_diff = NetDiffSerializer()
    series = SeriesPointSerializer(
        many=True,
        help_text=(
            "A fixed-size sampling of exactly `points` entries, not a paginated "
            "collection — so it gets no namespaced pagination triple in `meta`."
        ),
    )


class CashFlowSerializer(serializers.Serializer):
    inflow = MoneySerializer(
        help_text="A positive magnitude: what arrived.",
    )
    outflow = MoneySerializer(
        help_text="A positive magnitude: what left.",
    )
    total_net = MoneySerializer(
        help_text="`inflow - outflow`. Negative when more left than arrived.",
    )
    savings_rate = serializers.FloatField(
        allow_null=True,
        help_text=(
            "The share of income that was not spent, as a percentage — a bare "
            "number, not money. Null when nothing came in, where the rate is "
            "undefined rather than zero."
        ),
    )


class MetricsSerializer(serializers.Serializer):
    balance = BalanceSheetSerializer(
        allow_null=True,
        help_text="Null when `balance=false` was sent.",
    )
    net_worth = NetWorthSerializer(
        allow_null=True,
        help_text="Null when `net-worth=false` was sent.",
    )
    cash_flow = CashFlowSerializer(
        allow_null=True,
        help_text="Null when `cash-flow=false` was sent.",
    )


class MetricsMetaSerializer(serializers.Serializer):
    since = serializers.DateTimeField(
        allow_null=True,
        help_text="Echoed back. Null means all time, which is the default.",
    )
    points = serializers.IntegerField(
        help_text="How many series points were sampled.",
    )
    sections = serializers.ListField(
        child=serializers.CharField(),
        help_text="Which sections this response actually carries.",
    )
    cached = serializers.BooleanField(required=False)


class EnvelopedMetricsSerializer(serializers.Serializer):
    data = MetricsSerializer()
    meta = MetricsMetaSerializer()


def _section_flag(section) -> serializers.BooleanField:
    return serializers.BooleanField(
        required=False,
        default=True,
        help_text=(
            f"Include the `{section.key}` section. Every section defaults to "
            "true, so a bare request returns all three."
        ),
    )


class MetricsRequestSerializer(serializers.Serializer):
    since = serializers.DateTimeField(
        required=False,
        help_text=(
            "Day-zero for `net_worth`'s series and for `cash_flow`. Absent means "
            "all time. It does NOT bound `balance`, which is a snapshot."
        ),
    )
    points = serializers.IntegerField(
        required=False,
        default=PointsCount.DEFAULT_POINTS,
        min_value=PointsCount.MINIMUM_POINTS,
        max_value=PointsCount.MAXIMUM_POINTS,
        help_text=(
            f"Series length, clamped to {PointsCount.MINIMUM_POINTS}"
            f"..{PointsCount.MAXIMUM_POINTS} rather "
            "than rejected. `meta.points` reports what was applied."
        ),
    )

    def get_fields(self):
        fields = super().get_fields()
        for section in ALL_SECTIONS:
            fields[section.value] = _section_flag(section)

        return fields
