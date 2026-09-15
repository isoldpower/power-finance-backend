from .sandbox_identity import resolve_own_sandbox_id


class SandboxTrafficMatcher:
    """Who a process is, and whether a message is its own by strict equality.

    Consumers no longer filter with this directly — `build_sandbox_traffic_policy`
    decides that, and a baseline needs a broker lookup to answer. This stays as the
    identity itself: synchronous, and with no opinion about fallback.
    """

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
