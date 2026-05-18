from data_write_core.application.interfaces import EventBus
from data_write_core.infrastructure.messaging import InMemoryEventBus


def initialize_event_bus() -> EventBus:
    """Construct the process-wide EventBus and register its subscribers.
    No subscribers are wired today; add them here as cross-aggregate
    reactions land (cache invalidations, fraud-counter bumps, derived
    projections, …)."""
    event_bus = InMemoryEventBus()
    return event_bus
