"""Public API surface: top-level `kafka_client_py` re-exports.

Downstream services import these names directly. Pin the surface so a
reshuffle of internal modules can't accidentally drop or rename one.
"""

from __future__ import annotations

import kafka_client_py


def test_all_lists_the_documented_names():
    assert set(kafka_client_py.__all__) == {
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
        "envelope",
        "headers",
    }


def test_re_exports_are_the_same_objects_as_their_modules():
    # If a future refactor accidentally shadows a name with a re-import
    # cycle or wrapping decorator, identity diverges. Pin it.
    from kafka_client_py.consumer.dedupe.store import (
        CREATE_TABLE_SQL,
        DedupeStore,
        InMemoryDedupeStore,
        PostgresDedupeStore,
    )
    from kafka_client_py.consumer.handler import MessageHandler
    from kafka_client_py.consumer.message import ConsumedMessage
    from kafka_client_py.consumer.retry_policy import RetryPolicy
    from kafka_client_py.errors import (
        KafkaHandlerError,
        PoisonError,
        RetryExhaustedError,
        TransientError,
    )
    from kafka_client_py.publisher.dlq_publisher import DLQPublisher
    from kafka_client_py.publisher.publisher import AsyncPublisher, ProducerConfig
    from kafka_client_py.publisher.retry_publisher import RetryPublisher

    assert kafka_client_py.CREATE_TABLE_SQL is CREATE_TABLE_SQL
    assert kafka_client_py.AsyncPublisher is AsyncPublisher
    assert kafka_client_py.ConsumedMessage is ConsumedMessage
    assert kafka_client_py.DLQPublisher is DLQPublisher
    assert kafka_client_py.DedupeStore is DedupeStore
    assert kafka_client_py.InMemoryDedupeStore is InMemoryDedupeStore
    assert kafka_client_py.KafkaHandlerError is KafkaHandlerError
    assert kafka_client_py.MessageHandler is MessageHandler
    assert kafka_client_py.PoisonError is PoisonError
    assert kafka_client_py.PostgresDedupeStore is PostgresDedupeStore
    assert kafka_client_py.ProducerConfig is ProducerConfig
    assert kafka_client_py.RetryExhaustedError is RetryExhaustedError
    assert kafka_client_py.RetryPolicy is RetryPolicy
    assert kafka_client_py.RetryPublisher is RetryPublisher
    assert kafka_client_py.TransientError is TransientError


def test_headers_module_is_re_exported_for_dotted_access():
    # Consumers do `from kafka_client_py import headers as H` and then
    # H.HEADER_RETRY_COUNT. Pin that the module reference is the real one.
    from kafka_client_py import headers as headers_module

    assert headers_module is kafka_client_py.headers
    assert hasattr(headers_module, "HEADER_RETRY_COUNT")
