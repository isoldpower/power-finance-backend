from data_write_core.application.commands.config import ActionKind
from data_write_core.application.interfaces import EffectExecutor
from data_write_core.domain.automations import EffectType

from .notify import NotifyEffect
from .raise_action import AUTOMATION_RESOLUTIONS, RaiseActionEffect
from .set_category import SetCategoryEffect
from .transfer import TransferEffect

EFFECT_EXECUTORS: dict[str, EffectExecutor] = {
    EffectType.SET_CATEGORY: SetCategoryEffect(),
    EffectType.NOTIFY: NotifyEffect(),
    EffectType.RAISE_ACTION: RaiseActionEffect(),
    EffectType.TRANSFER: TransferEffect(),
}

__all__ = [
    "ActionKind.AUTOMATION",
    "AUTOMATION_RESOLUTIONS",
    "EFFECT_EXECUTORS",
    "EffectExecutor",
    "NotifyEffect",
    "RaiseActionEffect",
    "SetCategoryEffect",
    "TransferEffect",
]
