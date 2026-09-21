from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from write_service.common.money.config import MoneySettings

from .parsing import CURRENCY_AGNOSTIC_RULES, AmountCandidate, AmountRule


@extend_schema_field(OpenApiTypes.STR)
class MoneyAmountField(serializers.Field):
    rules: tuple[AmountRule, ...] = CURRENCY_AGNOSTIC_RULES

    default_error_messages = {
        "amount_malformed": (
            "Amount must be a canonical decimal string with no separators, "
            "exponent, or leading zeros."
        ),
        "amount_out_of_range": f"Integer part exceeds {MoneySettings.MAX_INTEGER_DIGITS} digits.",
    }

    def to_internal_value(self, data) -> Decimal:
        candidate = AmountCandidate(raw=data)
        for rule in self.rules:
            if not rule.is_satisfied_by(candidate):
                self.fail(str(rule.code))

        return Decimal(candidate.text)

    def to_representation(self, value) -> str:
        return str(value)
