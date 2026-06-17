"""Exception hierarchy: who-extends-whom is part of the public contract.

Downstream code catches `KafkaHandlerError` to opt into handler-related
errors broadly. Pin the tree so a refactor that flattens or re-parents
a class is caught here, not in a consumer that suddenly stops catching
RetryExhausted.
"""

from __future__ import annotations

from kafka_client_py.errors import (
    KafkaHandlerError,
    PoisonError,
    RetryExhaustedError,
    TransientError,
)


def test_kafka_handler_error_is_an_exception():
    assert issubclass(KafkaHandlerError, Exception)


def test_retry_exhausted_extends_kafka_handler_error():
    assert issubclass(RetryExhaustedError, KafkaHandlerError)


def test_transient_error_is_a_plain_exception_not_under_handler_error():
    assert issubclass(TransientError, Exception)
    assert not issubclass(TransientError, KafkaHandlerError)


def test_poison_error_is_a_plain_exception_not_under_handler_error():
    assert issubclass(PoisonError, Exception)
    assert not issubclass(PoisonError, KafkaHandlerError)


def test_transient_and_poison_are_distinct_types():
    assert not issubclass(TransientError, PoisonError)
    assert not issubclass(PoisonError, TransientError)


def test_errors_carry_messages_like_normal_exceptions():
    assert str(TransientError("blip")) == "blip"
    assert str(PoisonError("bad payload")) == "bad payload"
    assert str(RetryExhaustedError("gave up")) == "gave up"
    assert str(KafkaHandlerError("generic")) == "generic"
