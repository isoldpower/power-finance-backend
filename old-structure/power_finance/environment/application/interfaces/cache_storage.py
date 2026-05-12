from abc import ABC, abstractmethod
from typing import Callable, TypeVar


TValue = TypeVar("TValue", bound=object)

class CacheStorage(ABC):
    @abstractmethod
    async def get_data(self, callback: Callable[[], TValue], key: str | None = None) -> TValue:
        raise NotImplementedError()