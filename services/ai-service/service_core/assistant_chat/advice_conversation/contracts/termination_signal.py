from typing import Protocol, runtime_checkable

from .termination import Termination


@runtime_checkable
class TerminationSignal(Protocol):
    """Something outside the conversation that can end it."""

    def is_terminated(self) -> bool: ...

    def terminate(self, termination: Termination) -> None: ...

    async def wait(self) -> Termination: ...
