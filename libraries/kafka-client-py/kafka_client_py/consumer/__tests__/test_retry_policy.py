from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kafka_client_py import PoisonError, RetryPolicy, TransientError


def test_transient_error_is_always_retryable():
    p = RetryPolicy(retryable=())
    assert p.is_retryable(TransientError("blip")) is True


def test_poison_error_is_never_retryable():
    p = RetryPolicy(retryable=(ValueError,))
    assert p.is_retryable(PoisonError("bad payload")) is False


def test_user_retryable_tuple_respected():
    p = RetryPolicy(retryable=(ConnectionError,))
    assert p.is_retryable(ConnectionError()) is True
    assert p.is_retryable(ValueError()) is False


def test_backoff_grows_exponentially_within_cap():
    p = RetryPolicy(
        initial_backoff=timedelta(seconds=1),
        max_backoff=timedelta(seconds=60),
        backoff_multiplier=2.0,
        jitter_ratio=0.0,
    )
    assert p.compute_backoff(1) == timedelta(seconds=1)
    assert p.compute_backoff(2) == timedelta(seconds=2)
    assert p.compute_backoff(3) == timedelta(seconds=4)
    assert p.compute_backoff(10) == timedelta(seconds=60)


def test_compute_retry_at_uses_provided_now():
    p = RetryPolicy(
        initial_backoff=timedelta(seconds=5),
        backoff_multiplier=1.0,
        jitter_ratio=0.0,
    )
    now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
    assert p.compute_retry_at(1, now=now) == now + timedelta(seconds=5)


def test_jitter_stays_within_ratio_bounds():
    p = RetryPolicy(
        initial_backoff=timedelta(seconds=10),
        backoff_multiplier=1.0,
        jitter_ratio=0.2,
    )
    for _ in range(50):
        b = p.compute_backoff(1).total_seconds()
        assert 8.0 <= b <= 12.0


def test_a_transient_error_inside_an_exception_group_is_still_retryable():
    policy = RetryPolicy()

    group = BaseExceptionGroup("plan failed", [TransientError("blip"), TransientError("blip")])

    assert policy.is_retryable(group) is True


def test_a_configured_retryable_inside_an_exception_group_is_retryable():
    policy = RetryPolicy(retryable=(ConnectionError,))

    group = BaseExceptionGroup("plan failed", [ConnectionError(), ConnectionError()])

    assert policy.is_retryable(group) is True


def test_a_group_of_unknown_errors_is_not_retryable():
    policy = RetryPolicy()

    group = BaseExceptionGroup("plan failed", [ValueError(), ValueError()])

    assert policy.is_retryable(group) is False


def test_poison_anywhere_in_a_group_disqualifies_the_whole_group():
    policy = RetryPolicy()

    group = BaseExceptionGroup("plan failed", [TransientError("blip"), PoisonError("bad")])

    assert policy.is_retryable(group) is False
