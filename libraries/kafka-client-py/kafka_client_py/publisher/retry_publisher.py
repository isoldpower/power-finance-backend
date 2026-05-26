import traceback
from datetime import UTC, datetime

from .. import headers as Headers
from ..consumer.message import ConsumedMessage
from .publisher import AsyncPublisher

_ERROR_MESSAGE_MAX_LENGTH = 1024
_ERROR_STACK_MAX_LENGTH = 8192


class RetryPublisher:
    def __init__(
        self,
        publisher: AsyncPublisher,
        *,
        topic: str = "events.retry",
    ) -> None:
        self._publisher = publisher
        self._topic = topic

    async def publish(
        self,
        message: ConsumedMessage,
        *,
        error: BaseException,
        next_retry_at: datetime,
        attempt: int,
        first_failed_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> None:
        original_topic = (
            Headers.get(message.headers, Headers.HEADER_ORIGINAL_TOPIC) or message.topic
        )
        resolved_first_failed_at = (
            first_failed_at
            or Headers.get_datetime(message.headers, Headers.HEADER_FIRST_FAILED_AT)
            or datetime.now(UTC)
        )
        resolved_correlation_id = correlation_id or Headers.get(
            message.headers,
            Headers.HEADER_CORRELATION_ID,
        )

        republish_headers = Headers.merge(
            message.headers,
            (Headers.HEADER_ORIGINAL_TOPIC, original_topic),
            (Headers.HEADER_ORIGINAL_PARTITION, message.partition),
            (Headers.HEADER_ORIGINAL_OFFSET, message.offset),
            (Headers.HEADER_RETRY_COUNT, attempt),
            (Headers.HEADER_RETRY_AT, next_retry_at),
            (Headers.HEADER_FIRST_FAILED_AT, resolved_first_failed_at),
            (Headers.HEADER_FAILED_AT, datetime.now(UTC)),
            (Headers.HEADER_ERROR_CLASS, type(error).__name__),
            (Headers.HEADER_ERROR_MESSAGE, str(error)[:_ERROR_MESSAGE_MAX_LENGTH]),
            (
                Headers.HEADER_ERROR_STACK,
                _format_exception_traceback(error)[:_ERROR_STACK_MAX_LENGTH],
            ),
        )
        if resolved_correlation_id is not None:
            republish_headers = Headers.merge(
                republish_headers,
                (Headers.HEADER_CORRELATION_ID, resolved_correlation_id),
            )

        await self._publisher.publish(
            self._topic,
            key=message.key,
            value=message.value or b"",
            headers=republish_headers,
        )


def _format_exception_traceback(exception: BaseException) -> str:
    return "".join(
        traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__,
        )
    )
