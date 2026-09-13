from .sandbox_identity import resolve_own_sandbox_id


class SandboxTrafficMatcher:
    def __init__(self, own_sandbox_id: str | None) -> None:
        self._own_sandbox_id = own_sandbox_id

    @classmethod
    def from_environment(cls) -> "SandboxTrafficMatcher":
        return cls(resolve_own_sandbox_id())

    @property
    def own_sandbox_id(self) -> str | None:
        return self._own_sandbox_id

    @property
    def is_baseline(self) -> bool:
        return self._own_sandbox_id is None

    def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        return message_sandbox_id == self._own_sandbox_id
