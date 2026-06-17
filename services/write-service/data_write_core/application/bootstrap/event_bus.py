from data_write_core.application.interfaces import EventBus
from data_write_core.infrastructure.messaging import InMemoryEventBus


def initialize_event_bus() -> EventBus:
    event_bus = InMemoryEventBus()

    return event_bus
