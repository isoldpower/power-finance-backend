from abc import abstractmethod, ABC


class ServiceHealthChecker(ABC):
    @abstractmethod
    def health_status(self) -> str:
        raise NotImplementedError()