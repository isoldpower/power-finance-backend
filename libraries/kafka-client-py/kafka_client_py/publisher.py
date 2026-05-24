from dataclasses import dataclass
from typing import Self

from aiokafka import AIOKafkaProducer

from .headers import KafkaHeaders


@dataclass(slots=True)
class ProducerConfig:
    bootstrap_servers: str
    client_id: str | None = None
    acknowledgement_mode: str = "all"
    enable_idempotence: bool = True
    linger_milliseconds: int = 5
    compression_type: str | None = "gzip"


class AsyncPublisher:
    def __init__(self, config: ProducerConfig) -> None:
        self._config = config
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._config.bootstrap_servers,
            client_id=self._config.client_id,
            acks=self._config.acknowledgement_mode,
            enable_idempotence=self._config.enable_idempotence,
            linger_ms=self._config.linger_milliseconds,
            compression_type=self._config.compression_type,
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None

    async def publish(
        self,
        topic: str,
        *,
        value: bytes,
        key: bytes | None = None,
        headers: KafkaHeaders | None = None,
    ) -> None:
        if self._producer is None:
            raise RuntimeError("AsyncPublisher used before start()")
        await self._producer.send_and_wait(
            topic=topic,
            value=value,
            key=key,
            headers=headers or [],
        )

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()
