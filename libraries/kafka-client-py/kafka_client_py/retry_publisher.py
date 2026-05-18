"""Republish a failed message to `events.retry` with a delay marker.

The retry topic is *not* consumed for immediate processing — a dedicated retry
consumer reads it, sleeps until `x-retry-at`, then republishes the message back
to its original topic. That keeps the main consumer's lag clean and decouples
the delay from any single consumer process's lifetime.

Original key is preserved so the message lands on the same partition on
replay, which keeps per-aggregate ordering intact.
"""

from __future__ import annotations

import traceback
from datetime import UTC, datetime

from . import headers as H
from ._message import ConsumedMessage
from .publisher import AsyncPublisher


class RetryPublisher:
    def __init__(self, publisher: AsyncPublisher, *, topic: str = "events.retry") -> None:
        self._publisher = publisher
        self._topic = topic

    async def publish(
        self,
        msg: ConsumedMessage,
        *,
        error: BaseException,
        next_retry_at: datetime,
        attempt: int,
        first_failed_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Republish `msg` to the retry topic.

        `attempt` is the 1-indexed retry-topic attempt count *after* this publish.
        """
        original_topic = H.get(msg.headers, H.HEADER_ORIGINAL_TOPIC) or msg.topic
        first_failed = (
            first_failed_at
            or H.get_datetime(msg.headers, H.HEADER_FIRST_FAILED_AT)
            or datetime.now(UTC)
        )
        corr_id = correlation_id or H.get(msg.headers, H.HEADER_CORRELATION_ID)

        new_headers = H.merge(
            msg.headers,
            (H.HEADER_ORIGINAL_TOPIC, original_topic),
            (H.HEADER_ORIGINAL_PARTITION, msg.partition),
            (H.HEADER_ORIGINAL_OFFSET, msg.offset),
            (H.HEADER_RETRY_COUNT, attempt),
            (H.HEADER_RETRY_AT, next_retry_at),
            (H.HEADER_FIRST_FAILED_AT, first_failed),
            (H.HEADER_FAILED_AT, datetime.now(UTC)),
            (H.HEADER_ERROR_CLASS, type(error).__name__),
            (H.HEADER_ERROR_MESSAGE, str(error)[:1024]),
            (H.HEADER_ERROR_STACK, _trace(error)[:8192]),
        )
        if corr_id is not None:
            new_headers = H.merge(new_headers, (H.HEADER_CORRELATION_ID, corr_id))

        await self._publisher.publish(
            self._topic,
            key=msg.key,
            value=msg.value or b"",
            headers=new_headers,
        )


def _trace(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
