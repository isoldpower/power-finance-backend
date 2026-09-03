from collections.abc import AsyncIterator, Sequence

from .contracts import (
    ConnectionContext,
    MessageHandler,
    RoutedReplies,
)


class MessageRouter:
    def __init__(self, handlers: Sequence[MessageHandler]) -> None:
        self._handlers = tuple(handlers)

    async def route(self, message: dict, context: ConnectionContext) -> RoutedReplies:
        responsible = await self._responsible_handlers(message, context)

        return RoutedReplies(
            claimed=bool(responsible),
            frames=self._stream(responsible, message, context),
        )

    async def _responsible_handlers(
        self,
        message: dict,
        context: ConnectionContext,
    ) -> tuple[MessageHandler, ...]:
        responsible: list[MessageHandler] = []
        for handler in self._handlers:
            if not await handler.is_responsible(message, context):
                continue

            responsible.append(handler)
            if await handler.is_singleton(message, context):
                break

        return tuple(responsible)

    async def _stream(
        self,
        handlers: tuple[MessageHandler, ...],
        message: dict,
        context: ConnectionContext,
    ) -> AsyncIterator[dict]:
        for handler in handlers:
            async for frame in handler.handle(message, context):
                yield frame
