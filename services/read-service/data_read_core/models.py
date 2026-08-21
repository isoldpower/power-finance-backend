"""Django model-discovery shim."""

from data_read_core.shared.postgres_orm import (  # noqa: F401
    CurrencyReadModel,
    NotificationReadModel,
    TransactionReadModel,
    WalletReadModel,
    WebhookReadModel,
    WebhookSubscriptionReadModel,
)
from data_read_core.shared.read_at_least import (  # noqa: F401
    AppliedOutboxSeq,
)
