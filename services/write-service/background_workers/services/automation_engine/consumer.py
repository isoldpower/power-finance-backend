from kafka_consumer_py import KafkaConsumerRunner

from .config import AutomationEngineConfig
from .handler import handle_automation_event, logger


async def run_automation_engine(config: AutomationEngineConfig) -> None:
    runner = KafkaConsumerRunner(
        config.kafka,
        handle_automation_event,
        logger=logger,
        name="automation_engine",
    )

    await runner.run()
