from kafka_consumer_py import KafkaConsumerRunner
from observability import build_kafka_message_context_components

from .config import InboundConsumerConfig
from .handler import handle_notification_request, logger


async def run_inbound_notifications_consumer(config: InboundConsumerConfig) -> None:
    message_context = build_kafka_message_context_components()
    runner = KafkaConsumerRunner(
        config.kafka,
        handle_notification_request,
        logger=logger,
        name="inbound_notifications",
        context_binder=message_context.context_binder,
        traffic_policy=message_context.traffic_policy,
    )
    await runner.run()
