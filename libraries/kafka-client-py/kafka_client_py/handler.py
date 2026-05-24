import asyncio
from collections.abc import Awaitable, Callable

from ._message import ConsumedMessage
from .attempt_outcome import (
    AttemptOutcome,
    HandlerRaisedNonRetryable,
    HandlerRaisedPoison,
    HandlerRaisedRetryable,
    HandlerSucceeded,
)
from .dedupe import DedupeStore
from .dedupe_gate import DedupeGate, EventIdExtractor
from .dlq_publisher import DLQPublisher
from .errors import PoisonError
from .in_process_loop_state import InProcessLoopState
from .retry_context import RetryContext
from .retry_policy import RetryPolicy
from .retry_publisher import RetryPublisher
from .terminal_router import TerminalRouter

UserHandler = Callable[[ConsumedMessage], Awaitable[None]]


_IN_PROCESS_BACKOFF_SECONDS_PER_ATTEMPT = 0.1
_IN_PROCESS_BACKOFF_CEILING_SECONDS = 1.0


class MessageHandler:
    def __init__(
        self,
        user_handler: UserHandler,
        *,
        policy: RetryPolicy,
        retry_publisher: RetryPublisher,
        dlq_publisher: DLQPublisher,
        dedupe: DedupeStore | None = None,
        event_id: EventIdExtractor | None = None,
    ) -> None:
        self._user_handler = user_handler
        self._retry_policy = policy
        self._dedupe_gate = DedupeGate(
            dedupe_store=dedupe,
            event_id_extractor=event_id,
        )
        self._terminal_router = TerminalRouter(
            retry_policy=policy,
            retry_publisher=retry_publisher,
            dlq_publisher=dlq_publisher,
        )

    async def handle(self, message: ConsumedMessage) -> None:
        if await self._dedupe_gate.already_processed(message):
            return

        retry_context = RetryContext.from_message(message)
        last_retryable_exception = await self._run_in_process_attempts(
            message,
            retry_context,
        )

        if last_retryable_exception is None:
            return
        else:
            await self._terminal_router.route_terminal_failure(
                message,
                last_exception=last_retryable_exception,
                retry_context=retry_context,
                in_process_attempts_made=self._retry_policy.max_in_process_attempts,
            )

    async def _run_in_process_attempts(
        self,
        message: ConsumedMessage,
        retry_context: RetryContext,
    ) -> BaseException | None:
        loop_state = InProcessLoopState()

        for attempt_number in range(1, self._retry_policy.max_in_process_attempts + 1):
            attempt_outcome = await self._invoke_user_handler_once(message)
            await attempt_outcome.apply(
                loop_state=loop_state,
                terminal_router=self._terminal_router,
                message=message,
                retry_context=retry_context,
                attempt_number=attempt_number,
            )
            if loop_state.is_complete:
                return None
            if attempt_number < self._retry_policy.max_in_process_attempts:
                await self._sleep_between_in_process_attempts(attempt_number)

        return loop_state.last_retryable_exception

    async def _invoke_user_handler_once(self, message: ConsumedMessage) -> AttemptOutcome:
        try:
            await self._user_handler(message)
            return HandlerSucceeded()
        except PoisonError as poison_exception:
            return HandlerRaisedPoison(exception=poison_exception)
        except BaseException as raised_exception:
            if self._retry_policy.is_retryable(raised_exception):
                return HandlerRaisedRetryable(exception=raised_exception)
            return HandlerRaisedNonRetryable(exception=raised_exception)

    @staticmethod
    async def _sleep_between_in_process_attempts(attempt_number: int) -> None:
        await asyncio.sleep(
            min(
                _IN_PROCESS_BACKOFF_SECONDS_PER_ATTEMPT * attempt_number,
                _IN_PROCESS_BACKOFF_CEILING_SECONDS,
            )
        )
