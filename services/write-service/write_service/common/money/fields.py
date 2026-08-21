from decimal import Decimal

from rest_framework import serializers

from .parsing import CURRENCY_AGNOSTIC_RULES, MAX_INTEGER_DIGITS, AmountCandidate, AmountRule


class MoneyAmountField(serializers.Field):
    rules: tuple[AmountRule, ...] = CURRENCY_AGNOSTIC_RULES

    default_error_messages = {
        "amount_malformed": (
            "Amount must be a canonical decimal string with no separators, "
            "exponent, or leading zeros."
        ),
        "amount_out_of_range": f"Integer part exceeds {MAX_INTEGER_DIGITS} digits.",
    }

    def to_internal_value(self, data) -> Decimal:
        candidate = AmountCandidate(raw=data)
        for rule in self.rules:
            if not rule.is_satisfied_by(candidate):
                self.fail(str(rule.code))

        return Decimal(candidate.text)

    def to_representation(self, value) -> str:
        return str(value)
