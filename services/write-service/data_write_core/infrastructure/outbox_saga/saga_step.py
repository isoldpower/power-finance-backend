from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TForwardResult = TypeVar("TForwardResult")


class SagaStep(ABC, Generic[TForwardResult]):
    """One unit of work in a SAGA.

    `forward()` performs the step; `compensate()` undoes it. Both must be
    idempotent — the coordinator may retry, and an alerted operator may
    re-run a compensation manually after investigating an orphan."""

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def forward(self) -> TForwardResult:
        raise NotImplementedError()

    @abstractmethod
    async def compensate(self) -> None:
        raise NotImplementedError()


class OutboxSagaStep(SagaStep[int]):
    def __init__(self):
        self._appended_sequences: list[int] = []

    @abstractmethod
    async def forward(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def compensate(self) -> None:
        raise NotImplementedError()

    @property
    def last_appended_sequence(self) -> int:
        if not self._appended_sequences:
            raise RuntimeError(
                "OutboxSagaStep.last_appended_sequence read before forward() completed",
            )

        return self._appended_sequences[-1]
