from abc import ABC, abstractmethod
from datetime import timedelta


class WindowAlgorithm(ABC):
    @abstractmethod
    def calculate(self, request_id: str, period: timedelta):
        raise NotImplementedError()