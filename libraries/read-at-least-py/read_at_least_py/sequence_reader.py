from abc import ABC, abstractmethod


class AppliedSeqReader(ABC):
    """Reads the highest outbox seq the read side has applied for a scope."""

    @abstractmethod
    async def applied_seq(self, scope: str) -> int | None:
        raise NotImplementedError()
