from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..message import ConsumedMessage
from .in_process_loop_state import InProcessLoopState
from .retry_context import RetryContext
from .terminal_router import TerminalRouter


class AttemptOutcome(ABC):
    @abstractmethod
    async def apply(
        self,
        *,
        loop_state: InProcessLoopState,
        terminal_router: TerminalRouter,
        message: ConsumedMessage,
        retry_context: RetryContext,
        attempt_number: int,
    ) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class HandlerSucceeded(AttemptOutcome):
    async def apply(
        self,
        *,
        loop_state: InProcessLoopState,
        terminal_router: TerminalRouter,
        message: ConsumedMessage,
        retry_context: RetryContext,
        attempt_number: int,
    ) -> None:
        loop_state.mark_complete()


@dataclass(frozen=True)
class HandlerRaisedPoison(AttemptOutcome):
    exception: BaseException

    async def apply(
        self,
        *,
        loop_state: InProcessLoopState,
        terminal_router: TerminalRouter,
        message: ConsumedMessage,
        retry_context: RetryContext,
        attempt_number: int,
    ) -> None:
        await terminal_router.route_immediate_failure(
            message,
            exception=self.exception,
            retry_context=retry_context,
            in_process_attempts_made=attempt_number,
            reason="poison",
        )
        loop_state.mark_complete()


@dataclass(frozen=True)
class HandlerRaisedNonRetryable(AttemptOutcome):
    exception: BaseException

    async def apply(
        self,
        *,
        loop_state: InProcessLoopState,
        terminal_router: TerminalRouter,
        message: ConsumedMessage,
        retry_context: RetryContext,
        attempt_number: int,
    ) -> None:
        await terminal_router.route_immediate_failure(
            message,
            exception=self.exception,
            retry_context=retry_context,
            in_process_attempts_made=attempt_number,
            reason="non_retryable",
        )
        loop_state.mark_complete()


@dataclass(frozen=True)
class HandlerRaisedRetryable(AttemptOutcome):
    exception: BaseException

    async def apply(
        self,
        *,
        loop_state: InProcessLoopState,
        terminal_router: TerminalRouter,
        message: ConsumedMessage,
        retry_context: RetryContext,
        attempt_number: int,
    ) -> None:
        loop_state.record_retryable_exception(self.exception)


__all__ = [
    "AttemptOutcome",
    "HandlerRaisedNonRetryable",
    "HandlerRaisedPoison",
    "HandlerRaisedRetryable",
    "HandlerSucceeded",
]
