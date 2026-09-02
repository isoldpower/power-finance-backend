from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from ..refusal import (
    EFFECT_PARAMS_INVALID,
    EFFECT_SUBJECT_MISMATCH,
    AutomationRefusal,
)


class EffectRule(ABC):
    effect_type: str
    required_params: frozenset[str]
    subject: str | None = None

    def validate(self, params: Any, path: str) -> None:
        supplied = self._as_object(params, path)
        self._require_exact_params(supplied, path)
        self.check_values(supplied, path)

    def check_subject(self, subject: str, trigger_type: str, path: str) -> None:
        if self.subject is None or self.subject == subject:
            return

        raise AutomationRefusal(
            path=f"{path}.type",
            detail_code=EFFECT_SUBJECT_MISMATCH,
            reason=(
                f"`{self.effect_type}` cannot apply to a `{trigger_type}` trigger, "
                f"whose subject is {subject}."
            ),
        )

    @abstractmethod
    def check_values(self, params: Mapping[Any, Any], path: str) -> None:
        raise NotImplementedError()

    def _as_object(self, params: Any, path: str) -> Mapping[Any, Any]:
        match params:
            case {**supplied}:
                return supplied
            case _:
                raise AutomationRefusal(
                    path=path,
                    detail_code=EFFECT_PARAMS_INVALID,
                    reason="`params` must be an object.",
                )

    def _require_exact_params(self, supplied: Mapping[Any, Any], path: str) -> None:
        if set(supplied) == self.required_params:
            return

        raise AutomationRefusal(
            path=path,
            detail_code=EFFECT_PARAMS_INVALID,
            reason=(
                f"`{self.effect_type}` takes exactly {sorted(self.required_params)}; "
                f"got {sorted(supplied)}."
            ),
        )
