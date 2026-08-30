from kafka_consumer_py import KafkaConsumerRunner

from .config import FraudAlertsConsumerConfig
from .handler import FraudAlertHandler, logger
from .store import SuspendedUserStore


async def run_fraud_alerts_consumer(config: FraudAlertsConsumerConfig) -> None:
    store = SuspendedUserStore.from_config(config)
    handler = FraudAlertHandler(store)

    runner = KafkaConsumerRunner(
        config.kafka,
        handler.handle,
        logger=logger,
        name="fraud_alerts",
        closers=(store.close,),
    )
    await runner.run()
