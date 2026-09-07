from abc import ABC, abstractmethod

from ..rate_snapshot import RateSnapshot


class RateProvider(ABC):
    name: str

    @abstractmethod
    async def fetch(self, base_code: str) -> RateSnapshot:
        raise NotImplementedError()
