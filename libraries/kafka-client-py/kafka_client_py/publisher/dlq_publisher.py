from datetime import UTC, datetime

from .. import headers as Headers
from ..message import ConsumedMessage
from ._error_details import (
    ERROR_MESSAGE_MAX_BYTES,
    ERROR_STACK_MAX_BYTES,
    format_exception_traceback,
    truncate_utf8,
)
from .publisher import AsyncPublisher


class DLQPublisher:
    def __init__(
        self,
        publisher: AsyncPublisher,
        *,
        topic: str = "events.dlq",
    ) -> None:
        self._publisher = publisher
        self._topic = topic

    async def publish(
        self,
        message: ConsumedMessage,
        *,
        error: BaseException,
        total_attempts: int,
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

        dlq_headers = Headers.merge(
            message.headers,
            (Headers.HEADER_ORIGINAL_TOPIC, original_topic),
            (Headers.HEADER_ORIGINAL_PARTITION, message.partition),
            (Headers.HEADER_ORIGINAL_OFFSET, message.offset),
            (Headers.HEADER_RETRY_COUNT, total_attempts),
            (Headers.HEADER_FIRST_FAILED_AT, resolved_first_failed_at),
            (Headers.HEADER_FAILED_AT, datetime.now(UTC)),
            (Headers.HEADER_ERROR_CLASS, type(error).__name__),
            (Headers.HEADER_ERROR_MESSAGE, truncate_utf8(str(error), ERROR_MESSAGE_MAX_BYTES)),
            (
                Headers.HEADER_ERROR_STACK,
                truncate_utf8(format_exception_traceback(error), ERROR_STACK_MAX_BYTES),
            ),
        )

        if resolved_correlation_id:
            dlq_headers = Headers.merge(
                dlq_headers,
                (Headers.HEADER_CORRELATION_ID, resolved_correlation_id),
            )

        await self._publisher.publish(
            self._topic,
            key=message.key,
            value=message.value or b"",
            headers=dlq_headers,
        )
