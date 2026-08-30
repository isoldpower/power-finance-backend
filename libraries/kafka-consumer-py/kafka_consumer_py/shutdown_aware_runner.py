import asyncio
from collections.abc import Awaitable
from contextlib import suppress

from .types import ShutdownSignal


class ShutdownAwareRunner:
    def __init__(self, shutdown: ShutdownSignal) -> None:
        self._shutdown = shutdown

    async def run(self, work: Awaitable[None]) -> bool:
        work_task = asyncio.ensure_future(work)
        shutdown_task = asyncio.ensure_future(self._shutdown.wait())

        try:
            await asyncio.wait(
                {work_task, shutdown_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if work_task.done():
                return False

            work_task.cancel()
            with suppress(asyncio.CancelledError):
                await work_task
            return True
        finally:
            shutdown_task.cancel()
            with suppress(asyncio.CancelledError):
                await shutdown_task
