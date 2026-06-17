"""InProcessLoopState: the small mutable shared object the attempt loop
threads through every AttemptOutcome.apply().

Pin two contracts:
1. Initial state is "not complete, no recorded exception".
2. record_retryable_exception keeps only the LAST exception — used so
   the terminal router can publish the most recent error reason.
"""

from __future__ import annotations

from kafka_client_py.consumer.in_process_loop_state import InProcessLoopState


def test_initial_state_is_incomplete_with_no_exception():
    state = InProcessLoopState()

    assert state.is_complete is False
    assert state.last_retryable_exception is None


def test_mark_complete_flips_is_complete():
    state = InProcessLoopState()

    state.mark_complete()

    assert state.is_complete is True


def test_mark_complete_does_not_touch_exception():
    state = InProcessLoopState()
    boom = RuntimeError("recorded earlier")
    state.record_retryable_exception(boom)

    state.mark_complete()

    assert state.last_retryable_exception is boom


def test_record_retryable_exception_remembers_last():
    state = InProcessLoopState()
    first = ConnectionError("first")
    second = TimeoutError("second")

    state.record_retryable_exception(first)
    state.record_retryable_exception(second)

    assert state.last_retryable_exception is second


def test_record_retryable_exception_does_not_complete_the_loop():
    state = InProcessLoopState()

    state.record_retryable_exception(RuntimeError("blip"))

    assert state.is_complete is False
