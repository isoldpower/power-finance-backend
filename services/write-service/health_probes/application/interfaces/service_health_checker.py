from abc import ABC, abstractmethod


class ServiceHealthChecker(ABC):
    @abstractmethod
    async def health_status(self) -> str:
        raise NotImplementedError()
