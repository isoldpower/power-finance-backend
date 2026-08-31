import logging

from ..contracts import ConnectionContext, MessageHandler

GREETED_FIELD = "name"


class TempMessageHandler(MessageHandler):
    """Scaffolding: greets whoever the message names."""

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        return isinstance(message.get(GREETED_FIELD), str)

    async def handle(self, message: dict, context: ConnectionContext) -> str | None:
        self.logger.info("received websocket message: %s", message)

        return f"Hello, {message[GREETED_FIELD]}"
