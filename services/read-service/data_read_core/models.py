"""Django model-discovery shim."""

from data_read_core.shared.postgres_orm import (  # noqa: F401
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.read_at_least import (  # noqa: F401
    AppliedOutboxSeq,
)
