from collections.abc import Sequence

from .contracts import (
    ConnectionContext,
    MessageHandler,
    RoutedReplies,
)


class MessageRouter:
    def __init__(self, handlers: Sequence[MessageHandler]) -> None:
        self._handlers = tuple(handlers)

    async def route(self, message: dict, context: ConnectionContext) -> RoutedReplies:
        replies: list[str] = []
        message_claimed = False

        for handler in self._handlers:
            if await handler.is_responsible(message, context):
                message_claimed = True
                reply = await handler.handle(message, context)
                if reply is not None:
                    replies.append(reply)

                if await handler.is_singleton(message, context):
                    break

        return RoutedReplies(
            claimed=message_claimed,
            replies=tuple(replies),
        )
