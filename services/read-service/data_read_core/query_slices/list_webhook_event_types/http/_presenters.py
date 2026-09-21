from ..dtos import WebhookEventTypeDTO


def present_one(event_type: WebhookEventTypeDTO) -> dict:
    return {
        "event": event_type.event,
        "subject": event_type.subject,
        "description": event_type.description,
    }


def present_many(event_types: list[WebhookEventTypeDTO]) -> list[dict]:
    return [present_one(event_type) for event_type in event_types]
