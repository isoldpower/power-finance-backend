from collections.abc import Mapping
from typing import Any

from ...vocabulary import EffectType
from ..fields import require_non_empty_string, require_severity
from .base import EffectRule


class NotifyRule(EffectRule):
    effect_type = EffectType.NOTIFY
    required_params = frozenset({"severity", "title"})

    def check_values(self, params: Mapping[Any, Any], path: str) -> None:
        require_severity(params, path)
        require_non_empty_string(params, "title", path)
