from collections.abc import Sequence
from dataclasses import dataclass

from background_workers.services.kafka_consumer import ConsumerConfig


@dataclass(frozen=True, slots=True)
class FraudAlertsConsumerConfig:
    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    auto_offset_reset: str = "earliest"

    @property
    def kafka(self) -> ConsumerConfig:
        return ConsumerConfig(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            topics=self.topics,
            auto_offset_reset=self.auto_offset_reset,
        )
