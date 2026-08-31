import asyncio

from ..contracts import Termination


class ProcessShutdownSignal:
    def __init__(self) -> None:
        self._event = asyncio.Event()
        self._termination = Termination.server_shutting_down()

    def is_terminated(self) -> bool:
        return self._event.is_set()

    def terminate(self, termination: Termination) -> None:
        self._termination = termination
        self._event.set()

    async def wait(self) -> Termination:
        await self._event.wait()

        return self._termination
