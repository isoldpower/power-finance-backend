from rest_framework import serializers
from write_service.common.money import MoneyAmountField

from .config import HEX_COLOR, HelpText


def _colour_field(**kwargs):
    return serializers.RegexField(HEX_COLOR, help_text=HelpText.COLOR, **kwargs)


class CreateWalletRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    color = _colour_field(required=False, allow_blank=True)
    zero_balance = MoneyAmountField(required=False, help_text=HelpText.ZERO_BALANCE)
    opening_balance = MoneyAmountField(required=False, help_text=HelpText.OPENING_BALANCE)


class UpdateWalletRequestSerializer(serializers.Serializer):
    """Every field optional: an absent one is left alone, not cleared."""

    name = serializers.CharField(max_length=120, required=False)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    color = _colour_field(required=False, allow_blank=True)
    favorite = serializers.BooleanField(required=False)
    zero_balance = MoneyAmountField(required=False, help_text=HelpText.ZERO_BALANCE)


class ReplaceWalletRequestSerializer(serializers.Serializer):
    """PUT replaces the whole editable representation, so an omitted field
    resets to its default rather than being left alone."""

    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    color = _colour_field(required=False, allow_blank=True, default="")
    favorite = serializers.BooleanField(required=False, default=False)
    zero_balance = MoneyAmountField(required=False, default=None, help_text=HelpText.ZERO_BALANCE)
