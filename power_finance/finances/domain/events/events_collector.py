class EventCollector:
    def __init__(self) -> None:
        self._events = []

    def collect(self, event) -> None:
        self._events.append(event)

    def pull_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
