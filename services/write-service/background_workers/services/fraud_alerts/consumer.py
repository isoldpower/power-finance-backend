from background_workers.services.fraud_alerts.config import FraudAlertsConsumerConfig
from background_workers.services.fraud_alerts.handler import (
    FraudAlertHandler,
    logger,
)
from background_workers.services.fraud_alerts.store import SuspendedUserStore
from background_workers.services.kafka_consumer import KafkaConsumerRunner


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
