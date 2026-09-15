from .sandbox_group_registry import KafkaSandboxGroupRegistry


class StrictSandboxTrafficPolicy:
    """A sandbox takes its own traffic and nothing else.

    Unchanged on purpose: a sandbox runs a developer's edited code, so it must never
    process the baseline's events into the shared datastores.
    """

    def __init__(self, own_sandbox_id: str) -> None:
        self._own_sandbox_id = own_sandbox_id

    @property
    def own_sandbox_id(self) -> str | None:
        return self._own_sandbox_id

    async def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        return message_sandbox_id == self._own_sandbox_id


class BaselineFallbackTrafficPolicy:
    """The baseline takes untagged traffic, plus tagged traffic nobody is running.

    A developer routing read-service should not have to run ai-service, the webhook
    deliveries consumer and the automation engine just to keep their sandbox whole.
    So the question is asked per service: this consumer skips a sandbox's event only
    when that sandbox runs a consumer of its own *for this service*, and processes it
    otherwise. Exactly one consumer still handles each event per datastore.
    """

    def __init__(self, registry: KafkaSandboxGroupRegistry) -> None:
        self._registry = registry

    @property
    def own_sandbox_id(self) -> str | None:
        return None

    async def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        if not message_sandbox_id:
            return True

        return not await self._registry.has_consumer_for(message_sandbox_id)
