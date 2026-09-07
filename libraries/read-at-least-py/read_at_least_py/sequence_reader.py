from abc import ABC, abstractmethod


class AppliedSeqReader(ABC):
    @abstractmethod
    async def applied_seq(self, scope: str) -> int | None:
        raise NotImplementedError()
