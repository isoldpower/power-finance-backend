from typing import Protocol, runtime_checkable

from .termination import Termination


@runtime_checkable
class TerminationSignal(Protocol):
    def is_terminated(self) -> bool: ...

    def terminate(self, termination: Termination) -> None: ...

    async def wait(self) -> Termination: ...
