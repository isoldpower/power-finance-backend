"""Doubles for the ports a conversation talks through."""

import asyncio

from ..contracts import ConnectionContext, MessageHandler, Termination
from ..exceptions import ClientDisconnectedError, MalformedFrameError

CONTEXT = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_7")


class ScriptedTransport:
    """Replays a list of inbound frames, then behaves as the script says.

    An entry may be a dict (a frame), or an exception class to raise instead —
    which is how a test spells "the client hung up here".
    """

    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.sent: list[str] = []
        self.closed_with: Termination | None = None

    async def receive(self) -> dict:
        if not self._script:
            # Nothing left to say and nobody hung up: block, the way a real
            # socket does between messages.
            await asyncio.Event().wait()

        entry = self._script.pop(0)
        if isinstance(entry, type) and issubclass(entry, Exception):
            raise entry

        return entry

    async def send(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, termination: Termination) -> None:
        self.closed_with = termination


class DisconnectingTransport(ScriptedTransport):
    """Accepts frames but fails on the reply, as a peer that left mid-turn."""

    async def send(self, text: str) -> None:
        raise ClientDisconnectedError


class ImmediateSignal:
    """A termination signal that has already fired."""

    def __init__(self, termination: Termination | None = None) -> None:
        self._termination = termination or Termination.server_shutting_down()

    def is_terminated(self) -> bool:
        return True

    def terminate(self, termination: Termination) -> None:
        self._termination = termination

    async def wait(self) -> Termination:
        return self._termination


class RecordingHandler(MessageHandler):
    """Claims what it is told to claim, and records what it was asked."""

    def __init__(
        self,
        *,
        claims: bool = True,
        reply: str | None = "answered",
        singleton: bool = True,
        name: str = "recording",
    ) -> None:
        self._claims = claims
        self._reply = reply
        self._singleton = singleton
        self.name = name
        self.seen: list[dict] = []
        self.judged: list[dict] = []
        self.contexts: list[ConnectionContext] = []

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        self.judged.append(message)
        return self._claims

    async def handle(self, message: dict, context: ConnectionContext) -> str | None:
        self.seen.append(message)
        self.contexts.append(context)
        return self._reply

    async def is_singleton(self, message: dict, context: ConnectionContext) -> bool:
        return self._singleton


__all__ = [
    "CONTEXT",
    "ClientDisconnectedError",
    "DisconnectingTransport",
    "ImmediateSignal",
    "MalformedFrameError",
    "RecordingHandler",
    "ScriptedTransport",
]
