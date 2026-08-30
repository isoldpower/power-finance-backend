from kafka_consumer_py import KafkaConsumerRunner

from .config import InboundConsumerConfig
from .handler import handle_notification_request, logger


async def run_inbound_notifications_consumer(config: InboundConsumerConfig) -> None:
    runner = KafkaConsumerRunner(
        config.kafka,
        handle_notification_request,
        logger=logger,
        name="inbound_notifications",
    )
    await runner.run()
