from .exceptions import HandlerNotFoundError
from .types import EventMessage, Handler


class KafkaEventRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def has(self, event_type: str) -> bool:
        return event_type in self._handlers

    async def dispatch(self, event: EventMessage) -> None:
        handlers = self._handlers.get(event.event_type)
        if not handlers:
            raise HandlerNotFoundError(event.event_type)

        for handler in handlers:
            await handler(event)

    def registered_event_types(self) -> list[str]:
        return list(self._handlers)
