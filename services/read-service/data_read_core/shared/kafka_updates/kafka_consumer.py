from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord
from kafka_client_py import MessageHandler

from .logger_shortcuts import (
    except_commit_failed,
    except_event_handler_crashed,
    log_consumer_shutdown_signal,
    log_kafka_consumer_started,
    log_kafka_consumer_stopped,
)
from .shutdown_aware_runner import ShutdownAwareRunner
from .types import ShutdownSignal


class KafkaConsumerLoop:
    def __init__(
        self,
        consumer: AIOKafkaConsumer,
        message_handler: MessageHandler,
        shutdown: ShutdownSignal,
        *,
        poll_timeout_ms: int = 1_000,
    ) -> None:
        self._consumer = consumer
        self._message_handler = message_handler
        self._shutdown = shutdown
        self._poll_timeout_ms = poll_timeout_ms
        self._runner = ShutdownAwareRunner(shutdown)

    async def run(self) -> None:
        await self._consumer.start()
        log_kafka_consumer_started()

        try:
            while not self._shutdown.is_stop_requested():
                batches = await self._consumer.getmany(
                    timeout_ms=self._poll_timeout_ms,
                )

                if not batches:
                    continue
                for _, records_batch in batches.items():
                    for record in records_batch:
                        if self._shutdown.is_stop_requested():
                            return
                        if await self._process_or_shutdown(record):
                            return
        finally:
            await self._consumer.stop()
            log_kafka_consumer_stopped()

    async def _process_or_shutdown(self, record: ConsumerRecord) -> bool:
        interrupted = await self._runner.run(self._safe_process(record))
        if interrupted:
            log_consumer_shutdown_signal(record)

        return interrupted

    async def _safe_process(self, record: ConsumerRecord) -> None:
        try:
            await self._message_handler.handle(record)
        except Exception:
            except_event_handler_crashed(record)
            return
        await self._commit(record)

    async def _commit(self, record: ConsumerRecord) -> None:
        try:
            await self._consumer.commit()
        except Exception:
            except_commit_failed(record)
