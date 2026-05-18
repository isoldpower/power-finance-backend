from abc import ABC, abstractmethod


class SagaStep(ABC):
    """One unit of work in a SAGA.

    `forward()` performs the step; `compensate()` undoes it. Both must be
    idempotent — the coordinator may retry, and an alerted operator may
    re-run a compensation manually after investigating an orphan."""

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def forward(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def compensate(self) -> None:
        raise NotImplementedError()
