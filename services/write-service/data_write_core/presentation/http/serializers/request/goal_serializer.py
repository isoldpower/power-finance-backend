from rest_framework import serializers
from write_service.common.money import MoneyAmountField

TARGET_HELP = (
    "The amount the goal is saving towards, as a flat decimal string taking its "
    "currency from the goal. A money object in the response, a bare string here — "
    "the same asymmetry POST /transactions uses."
)
PROGRESS_HELP = (
    "Ignored if sent. Progress is derived from the transactions touching the goal, "
    "the same way a wallet's balance is, and no endpoint writes it."
)


class CreateGoalRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    currency = serializers.CharField(max_length=8)
    target = MoneyAmountField(help_text=TARGET_HELP)
    finish_at = serializers.DateTimeField(required=False, allow_null=True)


class UpdateGoalRequestSerializer(serializers.Serializer):
    """Every field optional: an absent one is left alone, not cleared.

    `currency` is absent on purpose — it is fixed at creation, and both `target` and
    `progress` are denominated in it. `progress` is accepted and discarded rather
    than rejected, which is what the target specifies.
    """

    name = serializers.CharField(max_length=120, required=False)
    target = MoneyAmountField(required=False, help_text=TARGET_HELP)
    finish_at = serializers.DateTimeField(required=False, allow_null=True)
    progress = serializers.CharField(required=False, help_text=PROGRESS_HELP)
