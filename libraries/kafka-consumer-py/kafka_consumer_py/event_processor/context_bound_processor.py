from kafka_client_py import ConsumedMessage

from ..message_context import MessageContextBinder
from ..types import MessageProcessor


class ContextBoundMessageProcessor:
    def __init__(
        self,
        inner_processor: MessageProcessor,
        context_binder: MessageContextBinder,
    ) -> None:
        self._inner_processor = inner_processor
        self._context_binder = context_binder

    async def __call__(self, message: ConsumedMessage) -> None:
        attachment_token = self._context_binder.bind(message.headers or ())

        try:
            await self._inner_processor(message)
        finally:
            self._context_binder.unbind(attachment_token)
