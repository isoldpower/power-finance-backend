from collections import defaultdict

from finances.application.interfaces import EventBus, EventHandler
from finances.domain.events import DomainEvent


class InMemoryEventBus(EventBus):
    _event_handlers: dict[type[DomainEvent], list[EventHandler]]

    def __init__(self):
        self._event_handlers = defaultdict(list)

    def subscribe(
            self,
            event_type: type[DomainEvent],
            event_handler: EventHandler
    ) -> None:
        self._event_handlers[event_type].append(event_handler)

    async def publish(self, events: list[DomainEvent]) -> None:
        for event in events:
            handlers = self._event_handlers.get(type(event), [])

            for handler in handlers:
                await handler(event)