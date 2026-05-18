"""Error-routing wrapper around a user-supplied async message handler.

Routing flow per message:

    dedupe.seen(event_id)?  -> skip silently
    user_handler(msg)       -> ok      -> done (caller commits offset)
                              transient -> in-process retry (with backoff)
                                          on exhaustion: events.retry  (if budget left)
                                                         events.dlq    (if budget spent)
                              poison    -> events.dlq immediately

The handler does NOT commit Kafka offsets. The caller (consumer loop) commits
after `handle()` returns *without raising*. If the handler raises, the loop
should NOT commit — re-deliver on next poll. The handler raises only on
internal failures (publisher down); business failures are always routed and
swallowed.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from . import headers as H
from ._message import ConsumedMessage
from .dedupe import DedupeStore
from .dlq_publisher import DLQPublisher
from .errors import PoisonError
from .retry_policy import RetryPolicy
from .retry_publisher import RetryPublisher

logger = logging.getLogger(__name__)


UserHandler = Callable[[ConsumedMessage], Awaitable[None]]
EventIdExtractor = Callable[[ConsumedMessage], str | None]


class MessageHandler:
    """Wraps a user handler with retry / DLQ / dedupe routing."""

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
        self._policy = policy
        self._retry = retry_publisher
        self._dlq = dlq_publisher
        self._dedupe = dedupe
        self._event_id = event_id

    async def handle(self, msg: ConsumedMessage) -> None:
        # Dedupe — skip messages already processed by this consumer group.
        if self._dedupe is not None and self._event_id is not None:
            eid = self._event_id(msg)
            if eid is not None and await self._dedupe.seen(eid):
                logger.debug("kafka.dedupe.skip", extra={"event_id": eid})
                return

        retry_topic_attempt = H.get_int(msg.headers, H.HEADER_RETRY_COUNT, default=0)
        first_failed_at = H.get_datetime(msg.headers, H.HEADER_FIRST_FAILED_AT)
        last_error: BaseException | None = None

        # In-process retry loop. Each iteration is a fresh user_handler call.
        for in_proc_attempt in range(1, self._policy.max_in_process_attempts + 1):
            try:
                await self._user_handler(msg)
                return
            except PoisonError as exc:
                # Terminal on first occurrence — straight to DLQ.
                await self._dlq.publish(
                    msg,
                    error=exc,
                    total_attempts=retry_topic_attempt + in_proc_attempt,
                    first_failed_at=first_failed_at or datetime.now(UTC),
                )
                logger.warning(
                    "kafka.handler.poison",
                    extra={"topic": msg.topic, "error_class": type(exc).__name__},
                )
                return
            except BaseException as exc:
                if not self._policy.is_retryable(exc):
                    await self._dlq.publish(
                        msg,
                        error=exc,
                        total_attempts=retry_topic_attempt + in_proc_attempt,
                        first_failed_at=first_failed_at or datetime.now(UTC),
                    )
                    logger.warning(
                        "kafka.handler.non_retryable",
                        extra={"topic": msg.topic, "error_class": type(exc).__name__},
                    )
                    return

                last_error = exc
                if in_proc_attempt < self._policy.max_in_process_attempts:
                    # Short in-process backoff scaled by attempt number, capped
                    # at 1 second — anything longer belongs on the retry topic.
                    await asyncio.sleep(min(0.1 * in_proc_attempt, 1.0))

        # In-process budget exhausted. Route based on retry-topic budget.
        assert last_error is not None
        total_in_proc = self._policy.max_in_process_attempts

        if retry_topic_attempt < self._policy.max_retry_topic_attempts:
            next_attempt = retry_topic_attempt + 1
            retry_at = self._policy.compute_retry_at(next_attempt)
            await self._retry.publish(
                msg,
                error=last_error,
                next_retry_at=retry_at,
                attempt=next_attempt,
                first_failed_at=first_failed_at or datetime.now(UTC),
            )
            logger.info(
                "kafka.handler.retry_scheduled",
                extra={
                    "topic": msg.topic,
                    "retry_at": retry_at.isoformat(),
                    "retry_topic_attempt": next_attempt,
                },
            )
            return

        # Retry-topic budget spent too — DLQ.
        await self._dlq.publish(
            msg,
            error=last_error,
            total_attempts=retry_topic_attempt + total_in_proc,
            first_failed_at=first_failed_at or datetime.now(UTC),
        )
        logger.warning(
            "kafka.handler.exhausted",
            extra={"topic": msg.topic, "total_attempts": retry_topic_attempt + total_in_proc},
        )
