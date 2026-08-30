from datetime import datetime

from aiokafka import ConsumerRecord
from kafka_client_py import ConsumedMessage

from ._logging import get_consumer_logger


def warn_routed_to_dlq(message: ConsumedMessage) -> None:
    logger = get_consumer_logger("consumer")
    logger.warning(
        "malformed envelope routed to DLQ; topic=%s partition=%s offset=%s",
        message.topic,
        message.partition,
        message.offset,
    )


def debug_no_event_handler(event_type: str, message: ConsumedMessage) -> None:
    logger = get_consumer_logger("consumer")
    logger.debug(
        "no handler registered; event_type=%s offset=%s — skipping",
        event_type,
        message.offset,
    )


def log_kafka_consumer_started() -> None:
    logger = get_consumer_logger("consumer")
    logger.info("Kafka consumer started")


def log_kafka_consumer_stopped() -> None:
    logger = get_consumer_logger("consumer")
    logger.info("Kafka consumer stopped")


def log_consumer_shutdown_signal(record: ConsumerRecord) -> None:
    logger = get_consumer_logger("consumer")
    logger.info(
        "shutdown requested; abandoned in-flight record "
        "topic=%s partition=%s offset=%s — will redeliver",
        record.topic,
        record.partition,
        record.offset,
    )


def except_event_handler_crashed(record: ConsumerRecord) -> None:
    logger = get_consumer_logger("consumer")
    logger.exception(
        "message_handler crashed; topic=%s partition=%s offset=%s "
        "— not committing, message will be redelivered",
        record.topic,
        record.partition,
        record.offset,
    )


def except_commit_failed(record: ConsumerRecord) -> None:
    logger = get_consumer_logger("consumer")
    logger.exception(
        "commit failed; topic=%s partition=%s offset=%s",
        record.topic,
        record.partition,
        record.offset,
    )


def log_shutdown_signal_received(signal: int) -> None:
    logger = get_consumer_logger("consumer")
    logger.info("received signal %s; requesting shutdown", signal)


def log_partition_held_for_retry(record: ConsumerRecord, until: datetime) -> None:
    logger = get_consumer_logger("consumer")
    logger.info(
        "retry not due until %s; holding topic=%s partition=%s at offset=%s",
        until.isoformat(),
        record.topic,
        record.partition,
        record.offset,
    )


def debug_partition_resumed(partition: object) -> None:
    logger = get_consumer_logger("consumer")
    logger.debug("retry due; resuming %s", partition)
