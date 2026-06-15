from enum import Enum


class WebhookType(str, Enum):
    """Event types a webhook endpoint can subscribe to."""

    TransactionCreate = "transaction.created"
    TransactionUpdate = "transaction.updated"
    TransactionDelete = "transaction.deleted"

    @classmethod
    def is_supported(cls, raw: str) -> bool:
        return raw in {member.value for member in cls}
