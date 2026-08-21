from abc import ABC, abstractmethod

from ..rate_snapshot import RateSnapshot


class RateProvider(ABC):
    """Where rates come from."""

    name: str

    @abstractmethod
    async def fetch(self, base_code: str) -> RateSnapshot:
        """The feed's current reading for `base_code`."""
        raise NotImplementedError()
