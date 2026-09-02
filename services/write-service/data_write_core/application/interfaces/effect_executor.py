from abc import ABC, abstractmethod
from typing import Any

from data_write_core.domain.automations import RunContext


class EffectExecutor(ABC):
    @abstractmethod
    async def apply(self, params: dict[str, Any], context: RunContext) -> None:
        raise NotImplementedError()
