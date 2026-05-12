from abc import abstractmethod, ABC


class ServiceHealthChecker(ABC):
    @abstractmethod
    async def health_status(self) -> str:
        raise NotImplementedError()