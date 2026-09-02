from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

Record = Mapping[str, Any]


class MatchNode(ABC):
    @abstractmethod
    def matches(self, record: Record) -> bool:
        raise NotImplementedError()
