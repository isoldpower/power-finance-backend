"""Cross-service contract for Kafka business events.

Importing from this package gives you the canonical message types every
producer and consumer agrees on. The wire format is currently Protobuf-
JSON (so Debezium's JSON converter can carry it without a Schema Registry
round-trip), but the contract is fixed by the underlying .proto files
under `proto/` — switching to binary + Schema Registry later won't change
the imports.
"""

from ._generated.transaction_pb2 import (
    TransactionCreated,
    TransactionDeleted,
)
from ._generated.wallet_pb2 import (
    WalletCreated,
    WalletDeleted,
    WalletUpdated,
)
from ._generated.webhook_pb2 import (
    WebhookDeliveryStatus,
    WebhookDeliveryStatusChanged,
)

__all__ = [
    "TransactionCreated",
    "TransactionDeleted",
    "WalletCreated",
    "WalletDeleted",
    "WalletUpdated",
    "WebhookDeliveryStatus",
    "WebhookDeliveryStatusChanged",
]
