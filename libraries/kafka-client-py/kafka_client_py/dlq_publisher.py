"""Publish a terminally-failed message to `events.dlq`.

DLQ messages are not auto-replayed. A separate operator tool (or admin
endpoint) inspects them and decides whether to fix-and-replay or drop.

Like the retry publisher, the original key is preserved.
"""

from __future__ import annotations

import traceback
from datetime import UTC, datetime

from . import headers as H
from ._message import ConsumedMessage
from .publisher import AsyncPublisher


class DLQPublisher:
    def __init__(self, publisher: AsyncPublisher, *, topic: str = "events.dlq") -> None:
        self._publisher = publisher
        self._topic = topic

    async def publish(
        self,
        msg: ConsumedMessage,
        *,
        error: BaseException,
        total_attempts: int,
        first_failed_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> None:
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
            (H.HEADER_RETRY_COUNT, total_attempts),
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
