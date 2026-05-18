"""Public API for kafka-client-py.

This iteration ships the error-routing primitives only:

* `RetryPolicy` — budgets + backoff math
* `RetryPublisher` / `DLQPublisher` — publish to events.retry / events.dlq
* `MessageHandler` — wraps a user handler with retry/DLQ/dedupe routing
* `DedupeStore` (+ `PostgresDedupeStore`, `InMemoryDedupeStore`)
* `AsyncPublisher` — minimal aiokafka producer wrapper used by the routers
* Header conventions in `kafka_client_py.headers`

Full consumer/producer wrappers come in a follow-up.
"""

from . import headers
from ._message import ConsumedMessage
from .dedupe import (
    CREATE_TABLE_SQL,
    DedupeStore,
    InMemoryDedupeStore,
    PostgresDedupeStore,
)
from .dlq_publisher import DLQPublisher
from .errors import (
    KafkaHandlerError,
    PoisonError,
    RetryExhaustedError,
    TransientError,
)
from .handler import EventIdExtractor, MessageHandler, UserHandler
from .publisher import AsyncPublisher, ProducerConfig
from .retry_policy import RetryPolicy
from .retry_publisher import RetryPublisher

__all__ = [
    "CREATE_TABLE_SQL",
    "AsyncPublisher",
    "ConsumedMessage",
    "DLQPublisher",
    "DedupeStore",
    "EventIdExtractor",
    "InMemoryDedupeStore",
    "KafkaHandlerError",
    "MessageHandler",
    "PoisonError",
    "PostgresDedupeStore",
    "ProducerConfig",
    "RetryExhaustedError",
    "RetryPolicy",
    "RetryPublisher",
    "TransientError",
    "UserHandler",
    "headers",
]
