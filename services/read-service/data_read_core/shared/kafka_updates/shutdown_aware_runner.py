import asyncio
from collections.abc import Awaitable
from contextlib import suppress

from .types import ShutdownSignal


class ShutdownAwareRunner:
    """Runs an awaitable, cancelling it if shutdown is requested first.

    Decouples "do this work" from "but stop promptly on shutdown": the work
    stays ignorant of the lifecycle, while this unit owns the race and the
    cancellation. Cancelled work is left incomplete — callers should treat that
    as "not done" (e.g. leave a Kafka offset uncommitted so it is redelivered).
    """

    def __init__(self, shutdown: ShutdownSignal) -> None:
        self._shutdown = shutdown

    async def run(self, work: Awaitable[None]) -> bool:
        """Await `work`; return True if shutdown interrupted it, else False."""
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
