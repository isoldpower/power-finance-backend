"""Django model-discovery shim.

The read-model definitions live under `data_read_core/_shared/read_models/`
(the shared read-store schema, consumed by both data_projections and
query_slices). Django only auto-imports `<app>.models`, so this re-export is
what registers them with the app and feeds makemigrations.
"""

from data_read_core._shared.postgres_orm import (  # noqa: F401
    TransactionReadModel,
    WalletReadModel,
)
