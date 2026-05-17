from ..events import DomainEvent, EventCollector


class EntityRoot:
    _designated_collector: EventCollector
    _unique_id: str

    def __init__(
        self,
        unique_id: str,
        collector: EventCollector,
    ) -> None:
        self._unique_id = unique_id
        self._designated_collector = collector

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def event_collector(self) -> EventCollector:
        return self._designated_collector

    def pull_events(self) -> list[DomainEvent]:
        return self._designated_collector.pull_events()

    def events_occurred(self, *events: DomainEvent) -> None:
        for event in events:
            self._designated_collector.collect(event)
