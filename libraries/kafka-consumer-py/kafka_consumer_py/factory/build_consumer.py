from aiokafka import AIOKafkaConsumer

from .types import ConsumerConfig


def build_aiokafka_consumer(config: ConsumerConfig) -> AIOKafkaConsumer:
    return AIOKafkaConsumer(
        *config.topics,
        bootstrap_servers=config.bootstrap_servers,
        group_id=config.group_id,
        enable_auto_commit=False,
        auto_offset_reset=config.auto_offset_reset,
        isolation_level=config.isolation_level,
        session_timeout_ms=config.session_timeout_ms,
        max_poll_interval_ms=config.max_poll_interval_ms,
        **config.extra,
    )
