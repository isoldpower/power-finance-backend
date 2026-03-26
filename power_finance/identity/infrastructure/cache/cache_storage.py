from abc import ABC, abstractmethod
from typing import Callable


class CacheStorage(ABC):
    @abstractmethod
    def get_data(self, callback: Callable[[], dict]) -> dict:
        raise NotImplementedError()