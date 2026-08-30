from collections.abc import Sequence
from dataclasses import dataclass

from kafka_consumer_py import ConsumerConfig


@dataclass(frozen=True, slots=True)
class InboundConsumerConfig:
    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    auto_offset_reset: str = "earliest"

    @property
    def kafka(self) -> ConsumerConfig:
        return ConsumerConfig(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            topics=self.topics,
            auto_offset_reset=self.auto_offset_reset,
        )
