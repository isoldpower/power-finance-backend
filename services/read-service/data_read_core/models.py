"""Django model-discovery shim."""

from data_read_core.shared.postgres_orm import (  # noqa: F401
    AccountDispatchReadModel,
    AccountPostingReadModel,
    AccountReadModel,
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
