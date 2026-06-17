"""AttemptOutcome subclasses: the four states an in-process attempt can land in.

Each outcome's `apply()` is the single line that wires the loop state
machine to the terminal router. Pin per-outcome behavior so a future
refactor of the loop body can't silently swap "log and continue" for
"route to DLQ".
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fakes import FakeMessage

from kafka_client_py.consumer.attempt_outcome import (
    HandlerRaisedNonRetryable,
    HandlerRaisedPoison,
    HandlerRaisedRetryable,
    HandlerSucceeded,
)
from kafka_client_py.consumer.in_process_loop_state import InProcessLoopState
from kafka_client_py.consumer.retry_context import RetryContext


def _ctx() -> RetryContext:
    return RetryContext(retry_topic_attempts_consumed=0, first_failed_at=None)


def _terminal_router_stub() -> AsyncMock:
    router = AsyncMock()
    router.route_immediate_failure = AsyncMock()
    router.route_terminal_failure = AsyncMock()
    return router


@pytest.mark.asyncio
async def test_handler_succeeded_marks_loop_complete():
    state = InProcessLoopState()
    router = _terminal_router_stub()

    await HandlerSucceeded().apply(
        loop_state=state,
        terminal_router=router,
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    assert state.is_complete is True


@pytest.mark.asyncio
async def test_handler_succeeded_does_not_route_anywhere():
    state = InProcessLoopState()
    router = _terminal_router_stub()

    await HandlerSucceeded().apply(
        loop_state=state,
        terminal_router=router,
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    router.route_immediate_failure.assert_not_awaited()
    router.route_terminal_failure.assert_not_awaited()


@pytest.mark.asyncio
async def test_poison_routes_to_immediate_failure_with_reason_poison():
    state = InProcessLoopState()
    router = _terminal_router_stub()
    boom = ValueError("bad payload")
    message = FakeMessage()
    ctx = _ctx()

    await HandlerRaisedPoison(exception=boom).apply(
        loop_state=state,
        terminal_router=router,
        message=message,
        retry_context=ctx,
        attempt_number=2,
    )

    router.route_immediate_failure.assert_awaited_once_with(
        message,
        exception=boom,
        retry_context=ctx,
        in_process_attempts_made=2,
        reason="poison",
    )


@pytest.mark.asyncio
async def test_poison_marks_loop_complete_so_caller_does_not_re_attempt():
    state = InProcessLoopState()
    router = _terminal_router_stub()

    await HandlerRaisedPoison(exception=ValueError()).apply(
        loop_state=state,
        terminal_router=router,
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    assert state.is_complete is True


@pytest.mark.asyncio
async def test_non_retryable_routes_to_immediate_failure_with_reason_non_retryable():
    state = InProcessLoopState()
    router = _terminal_router_stub()
    boom = RuntimeError("policy says no")
    ctx = _ctx()

    await HandlerRaisedNonRetryable(exception=boom).apply(
        loop_state=state,
        terminal_router=router,
        message=FakeMessage(),
        retry_context=ctx,
        attempt_number=3,
    )

    router.route_immediate_failure.assert_awaited_once()
    kwargs = router.route_immediate_failure.await_args.kwargs
    assert kwargs["exception"] is boom
    assert kwargs["reason"] == "non_retryable"
    assert kwargs["in_process_attempts_made"] == 3


@pytest.mark.asyncio
async def test_non_retryable_marks_loop_complete():
    state = InProcessLoopState()

    await HandlerRaisedNonRetryable(exception=RuntimeError()).apply(
        loop_state=state,
        terminal_router=_terminal_router_stub(),
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    assert state.is_complete is True


@pytest.mark.asyncio
async def test_retryable_records_exception_without_marking_complete():
    state = InProcessLoopState()
    boom = ConnectionError("blip")

    await HandlerRaisedRetryable(exception=boom).apply(
        loop_state=state,
        terminal_router=_terminal_router_stub(),
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    assert state.is_complete is False
    assert state.last_retryable_exception is boom


@pytest.mark.asyncio
async def test_retryable_does_not_call_terminal_router():
    router = _terminal_router_stub()

    await HandlerRaisedRetryable(exception=ConnectionError()).apply(
        loop_state=InProcessLoopState(),
        terminal_router=router,
        message=FakeMessage(),
        retry_context=_ctx(),
        attempt_number=1,
    )

    router.route_immediate_failure.assert_not_awaited()
    router.route_terminal_failure.assert_not_awaited()
