from kafka_consumer_py import KafkaConsumerRunner, build_sandbox_traffic_policy
from observability import build_kafka_message_context_components

from .config import AutomationEngineConfig
from .handler import handle_automation_event, logger


async def run_automation_engine(config: AutomationEngineConfig) -> None:
    message_context = build_kafka_message_context_components()
    runner = KafkaConsumerRunner(
        config.kafka,
        handle_automation_event,
        logger=logger,
        name="automation_engine",
        context_binder=message_context.context_binder,
        traffic_policy=build_sandbox_traffic_policy(
            config, message_context.traffic_policy.own_sandbox_id
        ),
    )

    await runner.run()
