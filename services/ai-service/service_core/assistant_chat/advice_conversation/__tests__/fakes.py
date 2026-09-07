import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from ..application.contracts import (
    ClientDisconnectedError,
    ConnectionContext,
    MalformedFrameError,
    MessageHandler,
    MessageRepository,
    ReferenceExtractor,
    ReplyGenerator,
    Termination,
)
from ..application.dtos import (
    ConversationMessageDTO,
    ResourceReferenceDTO,
    dtos_to_conversation_messages,
)
from ..domain.entities import ConversationMessage

CONTEXT = ConnectionContext(path="/api/v1/chat/advice", external_id="clerk_7")


class ScriptedTransport:
    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.sent: list[dict] = []
        self.closed_with: Termination | None = None

    async def receive(self) -> dict:
        if not self._script:
            await asyncio.Event().wait()

        entry = self._script.pop(0)
        if isinstance(entry, type) and issubclass(entry, Exception):
            raise entry

        return entry

    async def send(self, frame: dict) -> None:
        self.sent.append(frame)

    async def close(self, termination: Termination) -> None:
        self.closed_with = termination


class DisconnectingTransport(ScriptedTransport):
    async def send(self, frame: dict) -> None:
        raise ClientDisconnectedError


class ImmediateSignal:
    def __init__(self, termination: Termination | None = None) -> None:
        self._termination = termination or Termination.server_shutting_down()

    def is_terminated(self) -> bool:
        return True

    def terminate(self, termination: Termination) -> None:
        self._termination = termination

    async def wait(self) -> Termination:
        return self._termination


class RecordingHandler(MessageHandler):
    def __init__(
        self,
        *,
        claims: bool = True,
        reply: str | None = "answered",
        frames: tuple[dict, ...] | None = None,
        singleton: bool = True,
        name: str = "recording",
    ) -> None:
        self._claims = claims
        self._frames = (
            frames if frames is not None else () if reply is None else ({"reply": reply},)
        )
        self._singleton = singleton
        self.name = name
        self.seen: list[dict] = []
        self.judged: list[dict] = []
        self.contexts: list[ConnectionContext] = []

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        self.judged.append(message)
        return self._claims

    async def handle(
        self,
        message: dict,
        context: ConnectionContext,
    ) -> AsyncIterator[dict]:
        self.seen.append(message)
        self.contexts.append(context)
        for frame in self._frames:
            yield frame

    async def is_singleton(self, message: dict, context: ConnectionContext) -> bool:
        return self._singleton


class ExplodingHandler(MessageHandler):
    async def handle(
        self,
        message: dict,
        context: ConnectionContext,
    ) -> AsyncIterator[dict]:
        raise RuntimeError("handler is broken")
        yield {}


class ScriptedGenerator(ReplyGenerator):
    def __init__(self, *increments: str) -> None:
        self._increments = increments
        self.prompts: list[str] = []

    async def generate(
        self,
        prompt: str,
        context: ConnectionContext,
    ) -> AsyncIterator[str]:
        self.prompts.append(prompt)
        for increment in self._increments:
            yield increment


class FailingGenerator(ReplyGenerator):
    def __init__(self, *before_failing: str, failure: type[Exception] = RuntimeError) -> None:
        self._before_failing = before_failing
        self._failure = failure

    async def generate(
        self,
        prompt: str,
        context: ConnectionContext,
    ) -> AsyncIterator[str]:
        for increment in self._before_failing:
            yield increment

        raise self._failure("upstream is unreachable")


class StaticReferenceExtractor(ReferenceExtractor):
    def __init__(self, *references: ResourceReferenceDTO) -> None:
        self._references = references
        self.texts: list[str] = []

    async def extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReferenceDTO, ...]:
        self.texts.append(text)
        return self._references


class ExplodingReferenceExtractor(ReferenceExtractor):
    async def extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReferenceDTO, ...]:
        raise RuntimeError("reference lookup is broken")


class InMemoryMessageRepository(MessageRepository):
    def __init__(self) -> None:
        self.messages: dict[str, list[ConversationMessageDTO]] = {}

    async def append(self, external_id: str, message: ConversationMessageDTO) -> None:
        self.messages.setdefault(external_id, []).append(message)

    async def settle(
        self,
        message_id: UUID,
        status: str,
        text: str,
        refs: tuple[ResourceReferenceDTO, ...],
    ) -> None:
        for external_id, stored in self.messages.items():
            self.messages[external_id] = [
                ConversationMessageDTO(
                    id=message.id,
                    role=message.role,
                    status=status if message.id == message_id else message.status,
                    text=text if message.id == message_id else message.text,
                    created_at=message.created_at,
                    refs=refs if message.id == message_id else message.refs,
                )
                for message in stored
            ]

    async def page(
        self,
        external_id: str,
        limit: int,
        anchor: tuple | None = None,
        backwards: bool = False,
    ) -> list[ConversationMessageDTO]:
        return list(reversed(self.messages.get(external_id, [])))[: limit + 1]

    async def count(self, external_id: str) -> int:
        return len(self.messages.get(external_id, []))

    async def clear(self, external_id: str) -> int:
        return len(self.messages.pop(external_id, []))

    def stored(self, external_id: str = CONTEXT.external_id) -> list[ConversationMessage]:
        return dtos_to_conversation_messages(self.messages.get(external_id, []))


__all__ = [
    "CONTEXT",
    "ClientDisconnectedError",
    "DisconnectingTransport",
    "ExplodingHandler",
    "ExplodingReferenceExtractor",
    "FailingGenerator",
    "ImmediateSignal",
    "InMemoryMessageRepository",
    "MalformedFrameError",
    "RecordingHandler",
    "ScriptedGenerator",
    "ScriptedTransport",
    "StaticReferenceExtractor",
]
