from abc import ABC, abstractmethod

from ..dtos import OverviewDTO


class OverviewCache(ABC):
    @abstractmethod
    def get(self, external_id: str) -> OverviewDTO | None: ...

    @abstractmethod
    def put(self, external_id: str, overview: OverviewDTO) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...
