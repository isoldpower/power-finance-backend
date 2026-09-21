from rest_framework import serializers
from write_service.common.money import MoneyAmountField

from .config import HelpText


class CreateGoalRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    target = MoneyAmountField(help_text=HelpText.TARGET)
    finish_at = serializers.DateTimeField(required=False, allow_null=True)


class UpdateGoalRequestSerializer(serializers.Serializer):
    """Every field optional: an absent one is left alone, not cleared.

    `currency` is absent on purpose — it is fixed at creation, and both `target` and
    `progress` are denominated in it. `progress` is accepted and discarded rather
    than rejected, which is what the target specifies.
    """

    name = serializers.CharField(max_length=120, required=False)
    target = MoneyAmountField(required=False, help_text=HelpText.TARGET)
    finish_at = serializers.DateTimeField(required=False, allow_null=True)
    progress = serializers.CharField(required=False, help_text=HelpText.PROGRESS)
