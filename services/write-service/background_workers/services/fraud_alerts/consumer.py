from kafka_consumer_py import KafkaConsumerRunner
from observability import build_kafka_message_context_components

from .config import FraudAlertsConsumerConfig
from .handler import FraudAlertHandler, logger
from .store import SuspendedUserStore


async def run_fraud_alerts_consumer(config: FraudAlertsConsumerConfig) -> None:
    store = SuspendedUserStore.from_config(config)
    handler = FraudAlertHandler(store)

    message_context = build_kafka_message_context_components()
    runner = KafkaConsumerRunner(
        config.kafka,
        handler.handle,
        logger=logger,
        name="fraud_alerts",
        context_binder=message_context.context_binder,
        traffic_policy=message_context.traffic_policy,
        closers=(store.close,),
    )
    await runner.run()
