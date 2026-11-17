from collections.abc import Mapping
from typing import Any

from filter_grammar_py import FilterResource

from ...vocabulary import EffectType
from ..fields import require_uuid
from .base import EffectRule


class SetCategoryRule(EffectRule):
    effect_type = EffectType.SET_CATEGORY
    required_params = frozenset({"category_id"})
    subject = FilterResource.TRANSACTIONS

    def check_values(self, params: Mapping[Any, Any], path: str) -> None:
        require_uuid(params, "category_id", path)
