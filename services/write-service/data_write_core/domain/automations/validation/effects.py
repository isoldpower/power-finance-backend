from typing import Any

from data_write_core.domain.automations.validation.config import RefusalCode, RefusalPath

from ..vocabulary import EffectType, subject_of
from .refusal import (
    AutomationRefusal,
)
from .rules import rule_for


def validate_effects(effects: Any, trigger_type: str) -> None:
    match effects:
        case [_, *_] as entries:
            for index, effect in enumerate(entries):
                _validate_effect(
                    effect,
                    trigger_type,
                    f"{RefusalPath.EFFECTS}[{index}]",
                )
        case _:
            raise AutomationRefusal(
                path=RefusalPath.EFFECTS,
                detail_code=RefusalCode.REQUIRED,
                reason="A rule needs at least one effect.",
            )


def _validate_effect(effect: Any, trigger_type: str, path: str) -> None:
    match effect:
        case {"type": effect_type}:
            _validate_known_effect(effect, effect_type, trigger_type, path)
        case {}:
            raise _unknown_effect(f"{path}.type")
        case _:
            raise AutomationRefusal(
                path=path,
                detail_code=RefusalCode.EFFECT_UNKNOWN_TYPE,
                reason="An effect must be an object.",
            )


def _validate_known_effect(
    effect: dict[str, Any],
    effect_type: Any,
    trigger_type: str,
    path: str,
) -> None:
    rule = rule_for(effect_type)
    if rule is None:
        raise _unknown_effect(f"{path}.type")

    rule.check_subject(subject_of(trigger_type), trigger_type, path)
    rule.validate(effect.get("params"), f"{path}.params")


def _unknown_effect(path: str) -> AutomationRefusal:
    return AutomationRefusal(
        path=path,
        detail_code=RefusalCode.EFFECT_UNKNOWN_TYPE,
        reason=f"Unknown effect type. Legal values: {', '.join(EffectType)}.",
    )
