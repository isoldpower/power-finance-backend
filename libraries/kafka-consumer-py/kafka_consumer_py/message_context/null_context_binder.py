from .types import MessageHeaderPairs

UNBOUND_ATTACHMENT_TOKEN = object()


class NullMessageContextBinder:
    def bind(self, headers: MessageHeaderPairs) -> object:
        return UNBOUND_ATTACHMENT_TOKEN

    def unbind(self, attachment_token: object) -> None:
        return None

    def read_sandbox_id(self, headers: MessageHeaderPairs) -> str | None:
        return None
