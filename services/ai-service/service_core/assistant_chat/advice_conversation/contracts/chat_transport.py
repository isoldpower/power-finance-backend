from typing import Protocol, runtime_checkable

from .termination import Termination


@runtime_checkable
class ChatTransport(Protocol):
    async def receive(self) -> dict: ...

    async def send(self, frame: dict) -> None: ...

    async def close(self, termination: Termination) -> None: ...
