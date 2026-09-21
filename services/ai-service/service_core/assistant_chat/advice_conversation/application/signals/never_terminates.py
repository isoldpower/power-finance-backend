import asyncio

from ..contracts import Termination


class NeverTerminates:
    def is_terminated(self) -> bool:
        return False

    def terminate(self, termination: Termination) -> None: ...

    async def wait(self) -> Termination:
        await asyncio.Event().wait()

        raise AssertionError("unreachable: this signal never resolves")
