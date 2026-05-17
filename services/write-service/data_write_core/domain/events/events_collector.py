from ..exceptions import EventCollectorClosedError
from .domain_event import DomainEvent


class EventCollector:
    _events: list[DomainEvent]
    _collector_closed: bool

    def __init__(self) -> None:
        self._events = []
        self._collector_closed = False

    def collect(self, event: DomainEvent, close_after: bool = False) -> None:
        if self._collector_closed:
            raise EventCollectorClosedError()

        self._events.append(event)
        if close_after:
            self._collector_closed = True

    def pull_events(self, close_after: bool = False) -> list[DomainEvent]:
        events = self._events[:]
        self._events.clear()

        if close_after:
            self._collector_closed = True

        return events
