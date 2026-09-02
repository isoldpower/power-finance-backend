from webhook_catalog_py import event_values, is_known_event

WEBHOOK_EVENT_TYPES: frozenset[str] = event_values()


def is_subscribable_event(event: str) -> bool:
    return is_known_event(event)
