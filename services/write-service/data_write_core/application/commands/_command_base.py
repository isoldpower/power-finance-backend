from abc import ABC, abstractmethod
from typing import Protocol

from data_write_core.domain.events import DomainEvent
from data_write_core.infrastructure.outbox import emit_event


class _EventSource(Protocol):
    def pull_events(self) -> list[DomainEvent]: ...


class CommandHandlerBase(ABC):
    @abstractmethod
    async def handle(self, command):
        raise NotImplementedError()

    async def _publish_events(self, *sources: _EventSource) -> None:
        for source in sources:
            for event in source.pull_events():
                await emit_event(event)
