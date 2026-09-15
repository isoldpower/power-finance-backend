from kafka_client_py import ConsumedMessage

from ..logger_shortcuts import debug_foreign_sandbox_message_skipped
from ..message_context import MessageContextBinder, SandboxTrafficPolicy
from ..types import MessageProcessor


class SandboxFilteredMessageProcessor:
    def __init__(
        self,
        inner_processor: MessageProcessor,
        context_binder: MessageContextBinder,
        traffic_policy: SandboxTrafficPolicy,
    ) -> None:
        self._inner_processor = inner_processor
        self._context_binder = context_binder
        self._traffic_policy = traffic_policy

    async def __call__(self, message: ConsumedMessage) -> None:
        message_sandbox_id = self._context_binder.read_sandbox_id(message.headers or ())
        if not await self._traffic_policy.is_owned_traffic(message_sandbox_id):
            debug_foreign_sandbox_message_skipped(
                message,
                message_sandbox_id=message_sandbox_id,
                own_sandbox_id=self._traffic_policy.own_sandbox_id,
            )
            return

        await self._inner_processor(message)
