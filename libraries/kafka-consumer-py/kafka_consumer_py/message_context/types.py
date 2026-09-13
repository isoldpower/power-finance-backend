from collections.abc import Sequence
from typing import Protocol, runtime_checkable

MessageHeaderPairs = Sequence[tuple[str, bytes | None]]


@runtime_checkable
class MessageContextBinder(Protocol):
    def bind(self, headers: MessageHeaderPairs) -> object: ...

    def unbind(self, attachment_token: object) -> None: ...

    def read_sandbox_id(self, headers: MessageHeaderPairs) -> str | None: ...


@runtime_checkable
class SandboxTrafficPolicy(Protocol):
    @property
    def own_sandbox_id(self) -> str | None: ...

    def is_owned_traffic(self, message_sandbox_id: str | None) -> bool: ...
