from rest_framework import serializers
from write_service.common.money import MoneyAmountField

HEX_COLOR = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"

COLOR_HELP = "CSS hex colour, #RGB / #RRGGBB / #RRGGBBAA."
ZERO_BALANCE_HELP = (
    "The point the balance is measured from, as a flat decimal string taking "
    "its currency from the wallet. Not a floor: the balance may go below it, "
    "and what the user owns is the difference."
)
OPENING_BALANCE_HELP = (
    "What the wallet already held, as a flat decimal string. Recorded as an "
    "opening transaction, not stored on the wallet, so it is never echoed back. "
    "Defaults to `zero_balance`, which opens the wallet owning nothing."
)


def _colour_field(**kwargs):
    return serializers.RegexField(HEX_COLOR, help_text=COLOR_HELP, **kwargs)


class CreateWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    color = _colour_field(required=False, allow_blank=True)
    zero_balance = MoneyAmountField(required=False, help_text=ZERO_BALANCE_HELP)
    opening_balance = MoneyAmountField(required=False, help_text=OPENING_BALANCE_HELP)


class UpdateWalletRequestSerializer(serializers.Serializer):
    """Every field optional: an absent one is left alone, not cleared."""

    name = serializers.CharField(max_length=120, required=False)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    color = _colour_field(required=False, allow_blank=True)
    favorite = serializers.BooleanField(required=False)
    zero_balance = MoneyAmountField(required=False, help_text=ZERO_BALANCE_HELP)


class ReplaceWalletRequestSerializer(serializers.Serializer):
    """PUT replaces the whole editable representation, so an omitted field
    resets to its default rather than being left alone."""

    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    color = _colour_field(required=False, allow_blank=True, default="")
    favorite = serializers.BooleanField(required=False, default=False)
    zero_balance = MoneyAmountField(required=False, default=None, help_text=ZERO_BALANCE_HELP)
