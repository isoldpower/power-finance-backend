"""The closed set of things a rule can do.

Keyed by the wire string, which is what a stored rule carries. A type with no
executor is not silently skipped — the engine refuses to run the rule — because
a rule that appears to work and does nothing is the failure this vocabulary is
narrow to avoid.
"""

from data_write_core.application.interfaces import EffectExecutor
from data_write_core.domain.automations import EffectType

from .notify import NotifyEffect
from .raise_action import AUTOMATION_KIND, AUTOMATION_RESOLUTIONS, RaiseActionEffect
from .set_category import SetCategoryEffect
from .transfer import TransferEffect

EFFECT_EXECUTORS: dict[str, EffectExecutor] = {
    EffectType.SET_CATEGORY: SetCategoryEffect(),
    EffectType.NOTIFY: NotifyEffect(),
    EffectType.RAISE_ACTION: RaiseActionEffect(),
    EffectType.TRANSFER: TransferEffect(),
}

__all__ = [
    "AUTOMATION_KIND",
    "AUTOMATION_RESOLUTIONS",
    "EFFECT_EXECUTORS",
    "EffectExecutor",
    "NotifyEffect",
    "RaiseActionEffect",
    "SetCategoryEffect",
    "TransferEffect",
]
