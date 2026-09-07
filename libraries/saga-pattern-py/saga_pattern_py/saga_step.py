from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TForwardResult = TypeVar("TForwardResult")


class SagaStep(ABC, Generic[TForwardResult]):
    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def forward(self) -> TForwardResult:
        raise NotImplementedError()

    @abstractmethod
    async def compensate(self) -> None:
        raise NotImplementedError()
