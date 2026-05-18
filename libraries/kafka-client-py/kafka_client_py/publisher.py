"""Minimal async producer wrapper.

Scope: just enough to back `RetryPublisher` and `DLQPublisher`. A full producer
abstraction (envelope construction, schema validation, transactional output)
is intentionally out of scope for this module — those live next to the outbox
publisher and the per-service event emitters.

Lifecycle: `start()` once on service boot, `stop()` once on shutdown.
"""

from __future__ import annotations

from dataclasses import dataclass

from aiokafka import AIOKafkaProducer

from .headers import KafkaHeaders


@dataclass(slots=True)
class ProducerConfig:
    bootstrap_servers: str
    client_id: str | None = None
    acks: str = "all"  # never weaken: retry/DLQ losses are catastrophic
    enable_idempotence: bool = True
    linger_ms: int = 5
    compression_type: str | None = "gzip"


class AsyncPublisher:
    """Thin wrapper around `AIOKafkaProducer` returning awaitable sends."""

    def __init__(self, config: ProducerConfig) -> None:
        self._config = config
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._config.bootstrap_servers,
            client_id=self._config.client_id,
            acks=self._config.acks,
            enable_idempotence=self._config.enable_idempotence,
            linger_ms=self._config.linger_ms,
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

    async def __aenter__(self) -> AsyncPublisher:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()
