from .base import EventAutomationHandler
from .transaction import TransactionAutomationHandler

HANDLERS: tuple[EventAutomationHandler, ...] = (TransactionAutomationHandler(),)

EVENT_AUTOMATION_HANDLERS: dict[str, EventAutomationHandler] = {
    event_type: handler for handler in HANDLERS for event_type in handler.triggers
}

TRIGGER_BY_EVENT_TYPE: dict[str, str] = {
    event_type: trigger for handler in HANDLERS for event_type, trigger in handler.triggers.items()
}

__all__ = [
    "EVENT_AUTOMATION_HANDLERS",
    "HANDLERS",
    "TRIGGER_BY_EVENT_TYPE",
    "EventAutomationHandler",
    "TransactionAutomationHandler",
]
