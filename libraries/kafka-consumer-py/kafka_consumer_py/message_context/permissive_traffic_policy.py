class PermissiveSandboxTrafficPolicy:
    @property
    def own_sandbox_id(self) -> str | None:
        return None

    def is_owned_traffic(self, message_sandbox_id: str | None) -> bool:
        return True
