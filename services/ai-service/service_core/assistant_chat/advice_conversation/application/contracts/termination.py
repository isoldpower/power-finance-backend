from dataclasses import dataclass
from enum import Enum


class TerminationReason(Enum):
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    UNSUPPORTED_DATA = 1003
    POLICY_VIOLATION = 1008
    INTERNAL_ERROR = 1011


@dataclass(frozen=True, slots=True)
class Termination:
    reason: str
    code: TerminationReason
    announced: bool = True

    @classmethod
    def client_disconnected(cls) -> "Termination":
        return cls(
            reason="client_disconnected",
            code=TerminationReason.NORMAL_CLOSURE,
            announced=False,
        )

    @classmethod
    def server_shutting_down(cls) -> "Termination":
        return cls(
            reason="server_shutting_down",
            code=TerminationReason.GOING_AWAY,
        )

    @classmethod
    def unauthenticated(cls) -> "Termination":
        return cls(
            reason="unauthenticated",
            code=TerminationReason.POLICY_VIOLATION,
        )

    @classmethod
    def malformed_message(cls) -> "Termination":
        return cls(
            reason="malformed_message",
            code=TerminationReason.UNSUPPORTED_DATA,
        )

    @classmethod
    def unroutable_message(cls) -> "Termination":
        return cls(
            reason="unroutable_message",
            code=TerminationReason.UNSUPPORTED_DATA,
        )

    @classmethod
    def handler_failed(cls) -> "Termination":
        return cls(
            reason="handler_failed",
            code=TerminationReason.INTERNAL_ERROR,
        )
