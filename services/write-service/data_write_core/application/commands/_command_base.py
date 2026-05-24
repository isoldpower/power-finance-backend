from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar

from data_write_core.application.bootstrap import get_event_bus
from data_write_core.domain.events import DomainEvent


class _EventSource(Protocol):
    def pull_events(self) -> list[DomainEvent]: ...


THandler = TypeVar("THandler")


class CommandHandlerBase(ABC, Generic[THandler]):
    @abstractmethod
    async def handle(self, command) -> tuple[THandler, int]:
        raise NotImplementedError()

    async def _publish_domain_events(self, *sources: _EventSource) -> None:
        """Pulls domain events from each source and publishes them on
        the in-process EventBus. Call this AFTER the SAGA + outbox
        writes have committed — subscribers must only ever see events
        whose underlying state changes durably succeeded."""

        event_bus = get_event_bus()
        for source in sources:
            await event_bus.publish(source.pull_events())
