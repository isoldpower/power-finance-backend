import asyncio
from abc import ABC, abstractmethod
from logging import getLogger

logger = getLogger("background_workers.health")


class HealthProbe(ABC):
    """Checks availability of a downstream dependency."""

    def __init__(
        self,
        *,
        initial_poll_seconds: float = 1.0,
        max_poll_seconds: float = 30.0,
        backoff_multiplier: float = 2.0,
    ) -> None:
        self._initial_poll_seconds = initial_poll_seconds
        self._max_poll_seconds = max_poll_seconds
        self._backoff_multiplier = backoff_multiplier

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def is_healthy(self) -> bool:
        raise NotImplementedError()

    async def wait_until_healthy(self) -> None:
        poll_seconds = self._initial_poll_seconds
        while not await self.is_healthy():
            logger.warning(
                "%s still unavailable; next health check in %.1fs.",
                self.name,
                poll_seconds,
            )

            await asyncio.sleep(poll_seconds)
            poll_seconds = min(
                poll_seconds * self._backoff_multiplier,
                self._max_poll_seconds,
            )

        logger.info("%s available again; resuming.", self.name)
