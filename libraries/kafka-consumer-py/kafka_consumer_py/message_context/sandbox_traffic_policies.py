from .sandbox_group_registry import KafkaSandboxGroupRegistry


class StrictSandboxTrafficPolicy:
    """A sandbox takes its own traffic and nothing else."""

    def __init__(self, own_sandbox_id: str) -> None:
        self._own_sandbox_id = own_sandbox_id

    @property
    def own_sandbox_id(self) -> str | None:
        return self._own_sandbox_id

    async def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        return message_sandbox_id == self._own_sandbox_id


class BaselineFallbackTrafficPolicy:
    """The baseline takes untagged traffic, plus tagged traffic nobody is running."""

    def __init__(self, registry: KafkaSandboxGroupRegistry) -> None:
        self._registry = registry

    @property
    def own_sandbox_id(self) -> str | None:
        return None

    async def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        if not message_sandbox_id:
            return True

        return not await self._registry.has_consumer_for(message_sandbox_id)
