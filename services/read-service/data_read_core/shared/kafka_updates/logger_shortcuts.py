from aiokafka import ConsumerRecord
from kafka_client_py import ConsumedMessage

from data_read_core.shared.logging import get_workers_logger


def warn_routed_to_dlq(message: ConsumedMessage) -> None:
    logger = get_workers_logger(__name__)
    logger.warning(
        "malformed envelope routed to DLQ; topic=%s partition=%s offset=%s",
        message.topic,
        message.partition,
        message.offset,
    )


def debug_no_event_handler(event_type: str, message: ConsumedMessage) -> None:
    logger = get_workers_logger(__name__)
    logger.debug(
        "no handler registered; event_type=%s offset=%s — skipping",
        event_type,
        message.offset,
    )


def log_kafka_consumer_started() -> None:
    logger = get_workers_logger(__name__)
    logger.info("Kafka consumer started")


def log_kafka_consumer_stopped() -> None:
    logger = get_workers_logger(__name__)
    logger.info("Kafka consumer stopped")


def log_consumer_shutdown_signal(record: ConsumerRecord) -> None:
    logger = get_workers_logger(__name__)
    logger.info(
        "shutdown requested; abandoned in-flight record "
        "topic=%s partition=%s offset=%s — will redeliver",
        record.topic,
        record.partition,
        record.offset,
    )


def except_event_handler_crashed(record: ConsumerRecord) -> None:
    logger = get_workers_logger(__name__)
    logger.exception(
        "message_handler crashed; topic=%s partition=%s offset=%s "
        "— not committing, message will be redelivered",
        record.topic,
        record.partition,
        record.offset,
    )


def except_commit_failed(record: ConsumerRecord) -> None:
    logger = get_workers_logger(__name__)
    logger.exception(
        "commit failed; topic=%s partition=%s offset=%s",
        record.topic,
        record.partition,
        record.offset,
    )


def log_shutdown_signal_received(signal: int) -> None:
    logger = get_workers_logger(__name__)
    logger.info("received signal %s; requesting shutdown", signal)
