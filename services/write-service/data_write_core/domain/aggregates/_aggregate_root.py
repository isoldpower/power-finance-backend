from typing import Generic, TypeVar

from ..entities import EntityRoot
from ..events import DomainEvent, EventCollector

TRoot = TypeVar("TRoot", bound=EntityRoot)


class AggregateRoot(Generic[TRoot]):
    _root: TRoot

    def __init__(self, root: TRoot) -> None:
        self._root = root

    @property
    def root(self) -> TRoot:
        return self._root

    @property
    def unique_id(self) -> str:
        return self._root.unique_id

    @property
    def event_collector(self) -> EventCollector:
        return self._root.event_collector

    def pull_events(self) -> list[DomainEvent]:
        return self._root.pull_events()
