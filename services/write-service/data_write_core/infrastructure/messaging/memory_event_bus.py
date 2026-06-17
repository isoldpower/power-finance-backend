from collections import defaultdict
from typing import Any

from data_write_core.application.interfaces import AsyncEventHandler, EventBus
from data_write_core.application.interfaces.event_bus import EventType
from data_write_core.domain.events import DomainEvent


class InMemoryEventBus(EventBus):
    _event_handlers: dict[type[DomainEvent], list[Any]]

    def __init__(self) -> None:
        self._event_handlers = defaultdict(list)

    def subscribe(
        self,
        event_type: type[EventType],
        handler: AsyncEventHandler[EventType],
    ) -> None:
        self._event_handlers[event_type].append(handler)

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            handlers = self._event_handlers.get(type(event), [])
            for handler in handlers:
                await handler(event)
