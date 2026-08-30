import argparse

from kafka_consumer_py import ConsumerConfig

from .settings import WorkerSettings


def build_consumer_config(
    settings: WorkerSettings, arguments: argparse.Namespace
) -> ConsumerConfig:
    return ConsumerConfig(
        bootstrap_servers=arguments.bootstrap_servers,
        group_id=arguments.group_id,
        topics=arguments.topics
        or [
            settings.kafka_outbox_topic,
            settings.kafka_retry_topic,
        ],
        auto_offset_reset="earliest" if arguments.from_beginning else "latest",
    )
