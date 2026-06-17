import asyncio
import signal

from .logger_shortcuts import log_shutdown_signal_received


class SigtermShutdownSignal:
    """Concrete ShutdownSignal driven by SIGINT/SIGTERM"""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def install(self) -> None:
        running_loop = asyncio.get_running_loop()
        for signal_code in (signal.SIGINT, signal.SIGTERM):
            running_loop.add_signal_handler(
                signal_code,
                self._on_signal,
                signal_code,
            )

    def _on_signal(self, signal_code: int) -> None:
        log_shutdown_signal_received(signal_code)
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
