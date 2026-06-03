import asyncio
import logging
import signal

logger = logging.getLogger(__name__)


class SigtermShutdownSignal:
    """Concrete ShutdownSignal driven by SIGINT/SIGTERM"""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def install(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._on_signal, sig)

    def _on_signal(self, sig: int) -> None:
        logger.info("received signal %s; requesting shutdown", sig)
        self._event.set()

    def request_stop(self) -> None:
        self._event.set()

    def is_stop_requested(self) -> bool:
        return self._event.is_set()

    async def wait(self) -> None:
        await self._event.wait()


class NeverShutdown:
    """Test/lifetime-managed-elsewhere ShutdownSignal. Never stops on its own."""

    def is_stop_requested(self) -> bool:
        return False

    def request_stop(self) -> None: ...

    def install(self) -> None: ...

    async def wait(self) -> None:
        await asyncio.Event().wait()
