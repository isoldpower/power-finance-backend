"""The closed vocabulary of effects, one class each."""

from ...vocabulary import EffectType
from .base import EffectRule
from .notify import NotifyRule
from .raise_action import RaiseActionRule
from .set_category import SetCategoryRule
from .transfer import TransferRule

EFFECT_RULES: dict[str, EffectRule] = {
    rule.effect_type: rule
    for rule in (
        SetCategoryRule(),
        NotifyRule(),
        RaiseActionRule(),
        TransferRule(),
    )
}


def rule_for(effect_type: str) -> EffectRule | None:
    return EFFECT_RULES.get(effect_type)


__all__ = [
    "EFFECT_RULES",
    "EffectRule",
    "EffectType",
    "NotifyRule",
    "RaiseActionRule",
    "SetCategoryRule",
    "TransferRule",
    "rule_for",
]
