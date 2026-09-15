from typing import Protocol

from .message_context import (
    BaselineFallbackTrafficPolicy,
    KafkaSandboxGroupRegistry,
    SandboxTrafficPolicy,
    StrictSandboxTrafficPolicy,
)


class GroupedConsumerConfig(Protocol):
    """The two fields every consumer config carries, whatever else it holds.

    Write-service's consumers each define their own config type, so the builder asks
    for the shape rather than for one class.
    """

    @property
    def bootstrap_servers(self) -> str: ...

    @property
    def group_id(self) -> str: ...


def build_sandbox_traffic_policy(
    config: GroupedConsumerConfig,
    own_sandbox_id: str | None,
) -> SandboxTrafficPolicy:
    """A sandbox takes only its own traffic; the baseline covers whatever is unclaimed.

    `config.group_id` is already sandbox-scoped for a sandbox process, so the baseline
    is the only caller that derives candidate group names — from its own plain id.
    """
    if own_sandbox_id:
        return StrictSandboxTrafficPolicy(own_sandbox_id)

    return BaselineFallbackTrafficPolicy(
        KafkaSandboxGroupRegistry(
            bootstrap_servers=config.bootstrap_servers,
            own_group_id=config.group_id,
        )
    )
