from dataclasses import dataclass

from webhook_catalog_py import WebhookEventType


@dataclass(frozen=True)
class ListWebhookEventTypesQuery:
    """No user, no filters, no page. The catalog is the same for everyone."""


@dataclass(frozen=True)
class WebhookEventTypeDTO:
    event: str
    subject: str
    description: str

    @classmethod
    def from_catalog(cls, entry: WebhookEventType) -> "WebhookEventTypeDTO":
        return cls(
            event=entry.event,
            subject=entry.subject,
            description=entry.description,
        )
