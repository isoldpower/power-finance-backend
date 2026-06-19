from background_workers.services.inbound_notifications.config import InboundConsumerConfig
from background_workers.services.inbound_notifications.handler import (
    handle_notification_request,
    logger,
)
from background_workers.services.kafka_consumer import KafkaConsumerRunner


async def run_inbound_notifications_consumer(config: InboundConsumerConfig) -> None:
    runner = KafkaConsumerRunner(
        config.kafka,
        handle_notification_request,
        logger=logger,
        name="inbound_notifications",
    )
    await runner.run()
