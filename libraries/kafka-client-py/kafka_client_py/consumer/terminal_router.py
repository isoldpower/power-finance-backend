import logging

from ..publisher.dlq_publisher import DLQPublisher
from ..publisher.retry_publisher import RetryPublisher
from .message import ConsumedMessage
from .retry_context import RetryContext
from .retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class TerminalRouter:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy,
        retry_publisher: RetryPublisher,
        dlq_publisher: DLQPublisher,
    ) -> None:
        self._retry_policy = retry_policy
        self._retry_publisher = retry_publisher
        self._dlq_publisher = dlq_publisher

    async def route_immediate_failure(
        self,
        message: ConsumedMessage,
        *,
        exception: BaseException,
        retry_context: RetryContext,
        in_process_attempts_made: int,
        reason: str,
    ) -> None:
        total_attempts = retry_context.retry_topic_attempts_consumed + in_process_attempts_made
        await self._dlq_publisher.publish(
            message,
            error=exception,
            total_attempts=total_attempts,
            first_failed_at=retry_context.first_failed_at_or_now(),
        )
        logger.warning(
            "kafka.handler.%s topic=%s error=%s: %s",
            reason,
            message.topic,
            type(exception).__name__,
            exception,
            extra={"topic": message.topic, "error_class": type(exception).__name__},
        )

    async def route_terminal_failure(
        self,
        message: ConsumedMessage,
        *,
        last_exception: BaseException,
        retry_context: RetryContext,
        in_process_attempts_made: int,
    ) -> None:
        if self._retry_topic_budget_remaining(retry_context):
            await self._schedule_retry_topic_attempt(message, last_exception, retry_context)
            return
        await self._publish_exhausted_to_dlq(
            message, last_exception, retry_context, in_process_attempts_made
        )

    def _retry_topic_budget_remaining(self, retry_context: RetryContext) -> bool:
        return (
            retry_context.retry_topic_attempts_consumed
            < self._retry_policy.max_retry_topic_attempts
        )

    async def _schedule_retry_topic_attempt(
        self,
        message: ConsumedMessage,
        last_exception: BaseException,
        retry_context: RetryContext,
    ) -> None:
        next_retry_topic_attempt = retry_context.retry_topic_attempts_consumed + 1
        next_retry_at = self._retry_policy.compute_retry_at(next_retry_topic_attempt)
        await self._retry_publisher.publish(
            message,
            error=last_exception,
            next_retry_at=next_retry_at,
            attempt=next_retry_topic_attempt,
            first_failed_at=retry_context.first_failed_at_or_now(),
        )
        logger.info(
            "kafka.handler.retry_scheduled topic=%s retry_at=%s attempt=%s error=%s: %s",
            message.topic,
            next_retry_at.isoformat(),
            next_retry_topic_attempt,
            type(last_exception).__name__,
            last_exception,
            extra={
                "topic": message.topic,
                "retry_at": next_retry_at.isoformat(),
                "retry_topic_attempt": next_retry_topic_attempt,
                "error_class": type(last_exception).__name__,
            },
        )

    async def _publish_exhausted_to_dlq(
        self,
        message: ConsumedMessage,
        last_exception: BaseException,
        retry_context: RetryContext,
        in_process_attempts_made: int,
    ) -> None:
        total_attempts = retry_context.retry_topic_attempts_consumed + in_process_attempts_made
        await self._dlq_publisher.publish(
            message,
            error=last_exception,
            total_attempts=total_attempts,
            first_failed_at=retry_context.first_failed_at_or_now(),
        )
        logger.warning(
            "kafka.handler.exhausted topic=%s total_attempts=%s error=%s: %s",
            message.topic,
            total_attempts,
            type(last_exception).__name__,
            last_exception,
            extra={
                "topic": message.topic,
                "total_attempts": total_attempts,
                "error_class": type(last_exception).__name__,
            },
        )
