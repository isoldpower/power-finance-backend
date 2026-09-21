from typing import Protocol

from .message_context import (
    BaselineFallbackTrafficPolicy,
    KafkaSandboxGroupRegistry,
    SandboxTrafficPolicy,
    StrictSandboxTrafficPolicy,
)


class GroupedConsumerConfig(Protocol):
    @property
    def bootstrap_servers(self) -> str: ...

    @property
    def group_id(self) -> str: ...


def build_sandbox_traffic_policy(
    config: GroupedConsumerConfig,
    own_sandbox_id: str | None,
) -> SandboxTrafficPolicy:
    if own_sandbox_id:
        return StrictSandboxTrafficPolicy(own_sandbox_id)

    return BaselineFallbackTrafficPolicy(
        KafkaSandboxGroupRegistry(
            bootstrap_servers=config.bootstrap_servers,
            own_group_id=config.group_id,
        )
    )
